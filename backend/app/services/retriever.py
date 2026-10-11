"""Hybrid keyword and semantic retriever for MP Bhumi Vikas Rules."""
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.config import settings
from backend.app.services.document_store import DocumentStore, RuleChunk, RuleRecord

logger = logging.getLogger(__name__)

# Bilingual dictionary mapping Hindi terms to English regulatory vocabulary
HINDI_KEYWORD_MAP: Dict[str, str] = {
    "प्लॉट": "plot",
    "भूखंड": "plot",
    "वर्ग मीटर": "square meters sqm",
    "वर्गमीटर": "square meters sqm",
    "सड़क": "street road",
    "चौड़ी": "width wide street",
    "चौड़ाई": "width",
    "ऊँचाई": "height",
    "पिछला": "rear",
    "बगल": "side",
    "वैध": "valid duration sanction",
    "वैधता": "validity duration sanction",
    "दस्तावेज": "documents information accompanying application",
    "आवेदन": "application",
    "कृषि": "agricultural",
    "विकास अनुज्ञा": "development permission",
    "मार्ग": "road street",
    "आगे": "front",
    "सामने": "front",
    "पीछे": "rear",
    "किनारे": "side",
    "खाली": "open space setback",
    "खुला": "open space",
    "जगह": "space",
    "छोड़नी": "leave provide required",
    "परमिशन": "permission sanction",
    "अनुज्ञा": "permission sanction",
    "बिल्डिंग": "building",
    "भवन": "building",
    "फीस": "fee fees",
    "शुल्क": "fees charges",
    "नियम": "rule",
    "फार्म हाउस": "farm house",
    "बिजली": "electric overhead line",
    "विद्युत": "electric line",
    "तार": "electric line wire",
    "दूरी": "distance clearance",
    "बालकनी": "balcony verandah",
    "लिफ्ट": "lift elevator",
    "ऊंचाई": "height",
    "मंजिल": "storey floor",
    "मानचित्र": "plan",
    "नक्शा": "plan",
    "स्वीकृति": "sanction approval",
    "अवधि": "duration validity period",
    "नवीनीकरण": "renewal revalidation",
    "मास्टर प्लान": "development plan",
    "विकास योजना": "development plan",
    "समय सीमा": "deadline limitation period",
    "दुकान": "shop commercial",
    "मॉल": "mall",
    "आवासीय": "residential",
    "मकान": "residential house",
    "घर": "residential house",
    "बेसमेंट": "basement",
    "तहखाना": "basement",
    "पार्किंग": "parking",
    "सीढ़ी": "staircase",
    "जल": "water supply",
    "सीवरेज": "drainage sanitation",
    "दस्तखत": "signing submit architect engineer",
    "हस्ताक्षर": "sign submit architect engineer",
}

# English regulatory synonyms and phrase expansions
DOMAIN_SYNONYMS: Dict[str, str] = {
    "setback": "open space front rear side",
    "setbacks": "open space front rear side",
    "renew": "revalidation revalidate duration",
    "renewal": "revalidation revalidate duration",
    "validity": "duration sanction valid",
    "deadline": "limitation period thirty days deemed permission",
    "reply": "limitation period communication grant refusal",
    "disagree": "inconsistency development plan conflict prevail precedence",
    "conflict": "inconsistency development plan prevail precedence",
    "precedence": "inconsistency development plan prevail",
    "electric": "overhead line voltage clearance distance vertically horizontally",
    "balcony": "verandah projection electric line open space",
    "documents": "information accompanying application plans drawings ownership",
    "sign": "preparation signing of plans architect engineer supervisor",
    "submit": "preparation signing of plans application submission",
    "alteration": "deviation change alterations after sanction",
    "farm": "farm house agricultural",
    "fee": "fees permission fee",
    "charges": "fees",
    "my house": "residential building",
    "dwelling": "residential building",
    "change my plan": "deviation sanctioned plan alteration",
    "lift": "lifts escalators moving walks",
}


STOP_WORDS: Set[str] = {
    "what", "is", "the", "today", "for", "to", "in", "and", "a", "an", "of", "it", "on",
    "my", "i", "can", "do", "you", "are", "how", "much", "many", "does", "which", "when",
    "where", "who", "will", "be", "stay", "have", "not", "any", "at", "all", "so", "with",
    "from", "this", "that", "there", "these", "those", "their", "our",
    "का", "की", "के", "है", "हैं", "होगा", "होगी", "से", "में", "को", "और", "या", "पर", "एक", "तो", "भी"
}


# Score bands for retrieval confidence, calibrated on data/resources/sample_questions.md:
# in-scope questions score >= 0.4; off-topic and adversarial queries score below 0.3.
HIGH_CONFIDENCE_SCORE = 0.50
MEDIUM_CONFIDENCE_SCORE = 0.30


@dataclass
class RetrievalResult:
    """Retrieved document chunk with relevance metadata."""
    chunk_id: str
    rule_number: str
    rule_title: str
    part: str
    page_number: int
    text: str
    score: float
    confidence: str  # "high", "medium", "low"
    is_direct_rule_match: bool = False
    # Verbatim text just before this chunk in the same rule (headings, table captions)
    context: str = ""


class BM25Index:
    """Okapi BM25 implementation for exact keyword scoring."""

    def __init__(self, corpus_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_tokens = corpus_tokens
        self.N = len(corpus_tokens)
        self.doc_lens = [len(doc) for doc in corpus_tokens]
        self.avgdl = (sum(self.doc_lens) / self.N) if self.N > 0 else 1.0

        # Document frequencies
        df: Counter = Counter()
        for doc in corpus_tokens:
            for token in set(doc):
                df[token] += 1

        # Inverse document frequency
        self.idf: Dict[str, float] = {}
        for token, freq in df.items():
            self.idf[token] = math.log(1.0 + (self.N - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        """Compute BM25 scores for all documents in the corpus."""
        scores = [0.0] * self.N
        for idx, doc in enumerate(self.corpus_tokens):
            if not doc:
                continue
            doc_counts = Counter(doc)
            dl = self.doc_lens[idx]
            score = 0.0
            for t in query_tokens:
                if t in doc_counts:
                    tf = doc_counts[t]
                    w = self.idf.get(t, 0.1)
                    num = tf * (self.k1 + 1.0)
                    den = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avgdl))
                    score += w * (num / den)
            scores[idx] = score
        return scores


class RuleRetriever:
    """Hybrid BM25 + TF-IDF semantic retriever with bilingual Hindi/English handling."""

    def __init__(self, document_store: DocumentStore):
        self.doc_store = document_store
        self.chunks: List[RuleChunk] = self.doc_store.get_all_chunks()
        self.chunk_tokens: List[List[str]] = []
        self.chunk_texts: List[str] = []

        # Prepare corpus for BM25 and TF-IDF
        # The tail of the previous chunk of the same rule, so that table rows and clauses stay
        # associated with the heading that introduces them (e.g. "(2) Application Fee: ...").
        # Used for indexing and shown to the LLM as context before the passage.
        self.lead_ins: List[str] = []
        prev = None
        for ch in self.chunks:
            lead_in = self._lead_in(prev.text) if prev is not None and prev.rule_number == ch.rule_number else ""
            self.lead_ins.append(lead_in)
            enriched = f"Rule {ch.rule_number}. {ch.rule_title}. {ch.part}.\n{lead_in}\n{ch.text}"
            prev = ch
            self.chunk_texts.append(enriched)
            self.chunk_tokens.append(self.stem_tokens(self.preprocess_text(enriched)))
        self.title_tokens: List[Set[str]] = [
            {t for t in self.stem_tokens(self.preprocess_text(ch.rule_title)) if t not in STOP_WORDS and len(t) > 2}
            for ch in self.chunks
        ]

        self.bm25 = BM25Index(self.chunk_tokens)

        # TF-IDF Vectorizer for n-gram semantic phrase matching
        if self.chunk_texts:
            self.tfidf_vectorizer = TfidfVectorizer(
                ngram_range=(1, 3),
                max_features=12000,
                token_pattern=r"(?u)\b\w+\b",
                stop_words="english",
            )
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.chunk_texts)
        else:
            self.tfidf_vectorizer = None
            self.tfidf_matrix = None

    def preprocess_text(self, text: str) -> List[str]:
        """Tokenize text and extract words/numbers."""
        return re.findall(r"[a-zA-Z0-9_\u0900-\u097F]+", text.lower())

    @staticmethod
    def _lead_in(previous_text: str, limit: int = 300) -> str:
        """Last lines of the previous chunk, starting at a line boundary (verbatim)."""
        tail = previous_text[-limit:]
        if len(previous_text) > limit and "\n" in tail:
            tail = tail[tail.index("\n") + 1:]
        return tail.strip()

    @staticmethod
    def stem_tokens(tokens: List[str]) -> List[str]:
        """Very light English plural stemming (fees->fee, lifts->lift) for keyword matching."""
        out = []
        for t in tokens:
            if len(t) > 3 and t.isascii() and t.isalpha() and t.endswith("s") and not t.endswith("ss"):
                t = t[:-1]
            out.append(t)
        return out

    def expand_query(self, query: str) -> Tuple[List[str], Optional[str]]:
        """Expand Hindi/English terms and identify direct rule numbers."""
        lower_q = query.lower()
        expanded_terms: List[str] = []

        # Check for direct rule numbers: e.g. "Rule 56", "Rule 26-B", "नियम 17"
        rule_match = re.search(r"(?:rule|नियम|section|धारा)\s*[:#-]?\s*(\d{1,3}(?:-[A-Za-z])?)", query, re.IGNORECASE)
        target_rule = rule_match.group(1).upper() if rule_match else None

        # Check Hindi vocabulary mappings
        for hi_term, en_exp in HINDI_KEYWORD_MAP.items():
            if hi_term in lower_q:
                expanded_terms.extend(self.preprocess_text(en_exp))

        # Check English domain synonyms
        for kw, expansion in DOMAIN_SYNONYMS.items():
            if kw in lower_q:
                expanded_terms.extend(self.preprocess_text(expansion))

        raw_tokens = self.preprocess_text(query)
        # Filter stopwords
        filtered_tokens = [t for t in raw_tokens if t not in STOP_WORDS]
        filtered_tokens.extend(expanded_terms)
        return filtered_tokens, target_rule

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_threshold: float = settings.MIN_SIMILARITY_THRESHOLD,
    ) -> List[RetrievalResult]:
        """Perform hybrid retrieval for a query."""
        if not self.chunks:
            return []

        tokens, target_rule = self.expand_query(query)
        if not tokens:
            return []

        # 1. BM25 scores with soft saturation curve
        stemmed = self.stem_tokens(tokens)
        bm25_raw = self.bm25.get_scores(stemmed)
        bm25_norm = [s / (s + 12.0) for s in bm25_raw]

        # 2. TF-IDF Semantic scores
        tfidf_scores = [0.0] * len(self.chunks)
        if self.tfidf_vectorizer and self.tfidf_matrix is not None:
            query_str = " ".join(tokens)
            try:
                q_vec = self.tfidf_vectorizer.transform([query_str])
                cos_sims = cosine_similarity(q_vec, self.tfidf_matrix)[0]
                tfidf_scores = [float(s) for s in cos_sims]
            except Exception as e:
                logger.debug(f"TF-IDF similarity failed: {e}")

        # 3. Combine scores with boosts
        query_set = set(stemmed)
        combined_scores: List[Tuple[float, int, bool]] = []
        for idx, chunk in enumerate(self.chunks):
            # Hybrid fusion: 60% BM25, 40% TF-IDF
            score = 0.60 * bm25_norm[idx] + 0.40 * tfidf_scores[idx]
            is_rule_match = False

            # Strong boost if the rule number is explicitly queried
            if target_rule and chunk.rule_number.upper() == target_rule:
                score += 1.5
                is_rule_match = True

            # Boost by how much of the rule title the query covers
            title_tokens = self.title_tokens[idx]
            if title_tokens:
                score += 0.25 * len(title_tokens & query_set) / len(title_tokens)

            combined_scores.append((score, idx, is_rule_match))

        # Sort descending
        combined_scores.sort(key=lambda x: x[0], reverse=True)

        results: List[RetrievalResult] = []
        seen_chunks: Set[str] = set()

        for score, idx, is_rule_match in combined_scores:
            if len(results) >= top_k:
                break

            chunk = self.chunks[idx]
            if chunk.chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk.chunk_id)

            # Determine confidence
            if score >= HIGH_CONFIDENCE_SCORE or is_rule_match:
                confidence = "high"
            elif score >= max(min_threshold, MEDIUM_CONFIDENCE_SCORE):
                confidence = "medium"
            else:
                confidence = "low"

            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    rule_number=chunk.rule_number,
                    rule_title=chunk.rule_title,
                    part=chunk.part,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    score=score,
                    confidence=confidence,
                    is_direct_rule_match=is_rule_match,
                    context=self.lead_ins[idx],
                )
            )

        return results
