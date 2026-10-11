/**
 * Mock Data Repository for MP Bhumi Vikas Sahayak
 * Isolated mock responses for parallel frontend development and offline demonstration.
 * Complies with the schema:
 * {
 *   answer: string,
 *   language: string,
 *   citations: Array<{ document_title, rule_number, page_number, excerpt, source_url? }>,
 *   confidence: 'high' | 'medium' | 'low',
 *   insufficient_evidence: boolean,
 *   document_coverage_date: string
 * }
 */

export const mockResponses = {
  // 1. Setbacks for residential plots
  setback: {
    en: {
      answer: "Under Rule 52 of the Madhya Pradesh Bhumi Vikas Niyam, 2012, for a residential plot of 250 sq. meters, the mandatory marginal open spaces (setbacks) are:\n\n1. **Front Setback:** Minimum 3.0 meters from the plot boundary abutting the street.\n2. **Rear Setback:** Minimum 2.4 meters.\n3. **Side Setbacks:** Minimum 1.5 meters on one side, while the other side may abut the boundary or require 1.2 meters depending on whether the building is semi-detached.\n\nAll setbacks must remain open to the sky, free from permanent load-bearing structures except permissible architectural projections (sunshades up to 0.6m) as defined under Rule 54.",
      language: "en",
      citations: [
        {
          document_title: "Madhya Pradesh Bhumi Vikas Niyam, 2012 (Directorate of Town & Country Planning)",
          rule_number: "Rule 52, Table No. 13 - Marginal Open Spaces for Residential Buildings",
          page_number: 48,
          excerpt: "For residential plots having an area exceeding 150 sq. metres but not exceeding 300 sq. metres, the minimum front open space shall be 3.0 metres, rear open space shall be 2.4 metres, and side open space shall be 1.5 metres on at least one side.",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=48"
        },
        {
          document_title: "MP Bhumi Vikas Niyam, 2012 (General Architectural Projections)",
          rule_number: "Rule 54 - Permissible Projections into Open Spaces",
          page_number: 52,
          excerpt: "Cornices, chhajjas, or weather shades may project into the required open space up to a width of 0.60 metre, provided that a minimum vertical clearance of 2.1 metres from ground level is preserved.",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=52"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    },
    hi: {
      answer: "मध्य प्रदेश भूमि विकास नियम, 2012 के नियम 52 (तालिका क्र. 13) के अनुसार, 250 वर्ग मीटर क्षेत्रफल वाले आवासीय भूखंड के लिए अनिवार्य सीमांत खुले स्थान (सेटबैक) निम्नलिखित हैं:\n\n1. **अग्र सेटबैक (Front Setback):** सड़क से सटी सीमा से न्यूनतम 3.0 मीटर।\n2. **पश्च सेटबैक (Rear Setback):** न्यूनतम 2.4 मीटर।\n3. **पार्श्व सेटबैक (Side Setback):** कम से कम एक तरफ न्यूनतम 1.5 मीटर।\n\nनियम 54 के अनुसार इन खुले स्थानों में केवल 0.6 मीटर तक के छज्जे/सनशेड अनुमेय हैं, किसी भी स्थायी निर्माण की अनुमति नहीं है।",
      language: "hi",
      citations: [
        {
          document_title: "मध्य प्रदेश भूमि विकास नियम, 2012 (नगर तथा ग्राम निवेश विभाग)",
          rule_number: "नियम 52, तालिका 13 - आवासीय भवनों हेतु सीमांत खुले स्थान",
          page_number: 48,
          excerpt: "150 वर्ग मीटर से अधिक तथा 300 वर्ग मीटर तक के आवासीय भूखंडों के लिए अग्र खुला स्थान न्यूनतम 3.0 मीटर, पश्च खुला स्थान 2.4 मीटर तथा कम से कम एक ओर 1.5 मीटर पार्श्व खुला स्थान रखना अनिवार्य होगा।",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=48"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    }
  },

  // 2. Commercial FAR for 18m road
  far: {
    en: {
      answer: "According to Rule 60 and Schedule IV of the MP Bhumi Vikas Niyam, 2012 (with amendments):\n\n1. **Base Permissible FAR:** For commercial buildings on roads with a right-of-way of 18 meters or more, the standard permissible FAR is **1:1.75** (or 1.75).\n2. **Purchasable / Premium FAR:** Additional FAR up to 0.5 may be availed subject to payment of the prescribed compounding fee to the competent planning authority, bringing the effective FAR up to **2.25** in designated commercial zones.\n3. **Ground Coverage:** The maximum permissible ground coverage is capped at **40% to 50%**, ensuring requisite vehicular maneuvering and setbacks.",
      language: "en",
      citations: [
        {
          document_title: "Madhya Pradesh Bhumi Vikas Niyam, 2012",
          rule_number: "Rule 60, Table No. 16 - Floor Area Ratio (FAR) for Non-Residential Buildings",
          page_number: 63,
          excerpt: "For commercial activities abutting a road of minimum width 18 metres, the maximum permissible FAR shall be 1.75. In cases where the local Development Plan provides for premium FAR, an additional FAR not exceeding 0.50 may be permitted upon payment of prescribed premium rates.",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=63"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    },
    hi: {
      answer: "मध्य प्रदेश भूमि विकास नियम, 2012 के नियम 60 एवं अनुसूची IV के अनुसार:\n\n1. **मूल अनुमेय FAR:** 18 मीटर या उससे अधिक चौड़ी सड़क पर स्थित व्यावसायिक भवनों के लिए मानक FAR **1:1.75** (1.75) है।\n2. **प्रीमियम FAR:** सक्षम प्राधिकारी को निर्धारित शुल्क का भुगतान कर अधिकतम 0.50 तक अतिरिक्त FAR प्राप्त किया जा सकता है, जिससे कुल FAR **2.25** तक हो सकता है।\n3. **भू-आच्छादन (Ground Coverage):** अधिकतम 40% से 50% तक सीमित है।",
      language: "hi",
      citations: [
        {
          document_title: "मध्य प्रदेश भूमि विकास नियम, 2012",
          rule_number: "नियम 60, तालिका 16 - गैर-आवासीय भवनों हेतु FAR",
          page_number: 63,
          excerpt: "18 मीटर न्यूनतम मार्ग चौड़ाई पर व्यावसायिक भवनों के लिए मानक FAR 1.75 होगा। प्रीमियम FAR नीति के तहत अधिकतम 0.5 अतिरिक्त FAR अनुमेय हो सकता है।",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=63"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    }
  },

  // 3. Row housing side setbacks
  row_housing: {
    en: {
      answer: "Under Rule 52(4) of the MP Bhumi Vikas Niyam, 2012, for row-housing developments:\n\n* **Side setbacks are NOT mandatory between internal units in a contiguous row.** The side walls between adjacent row units may be built as common party walls abutting the boundary.\n* **End Units Requirement:** For the terminal or end plots of any continuous row, a minimum side setback of **1.5 meters** is mandatory.\n* **Row Length Limit:** The maximum continuous length of a row-housing block must not exceed **45 meters**, after which an open passage of at least 3.0 meters must be provided.",
      language: "en",
      citations: [
        {
          document_title: "MP Bhumi Vikas Niyam, 2012",
          rule_number: "Rule 52(4) - Special Provisions for Row Housing and Group Housing",
          page_number: 50,
          excerpt: "In row-housing schemes, side open spaces between interior plots are dispensed with, provided the plots on both extremities of the block leave a minimum side open space of not less than 1.5 metres. No continuous row shall exceed 45 metres in length.",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=50"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    },
    hi: {
      answer: "म.प्र. भूमि विकास नियम, 2012 के नियम 52(4) के अनुसार पंक्तिबद्ध आवास (Row Housing) हेतु:\n\n* पंक्ति के आंतरिक भूखंडों के बीच **पार्श्व सेटबैक अनिवार्य नहीं है**, और साझा दीवार (Party Wall) का निर्माण किया जा सकता है।\n* पंक्ति के दोनों अंतिम छोर वाले भूखंडों (End Plots) पर न्यूनतम **1.5 मीटर** का पार्श्व सेटबैक छोड़ना अनिवार्य है।\n* किसी भी पंक्ति की कुल निरंतर लंबाई **45 मीटर** से अधिक नहीं हो सकती।",
      language: "hi",
      citations: [
        {
          document_title: "म.प्र. भूमि विकास नियम, 2012",
          rule_number: "नियम 52(4) - पंक्तिबद्ध आवास संबंधी विशेष प्रावधान",
          page_number: 50,
          excerpt: "पंक्तिबद्ध आवास में आंतरिक भूखंडों के मध्य पार्श्व खुला स्थान अपेक्षित नहीं है, बशर्ते अंतिम भूखंडों पर 1.5 मीटर खुला स्थान छोड़ा जाए। निरंतर पंक्ति 45 मीटर से अधिक लंबी नहीं होगी।",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=50"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    }
  },

  // 4. Building permission documents & structural certificates
  permission: {
    en: {
      answer: "Under Rule 17 and Rule 21 of MP Bhumi Vikas Niyam, 2012, an application for Building Permission (Form 2) must be accompanied by:\n\n1. **Proof of Ownership:** Certified copies of Registered Sale Deed / Lease Deed and latest Khasra/Khatauni/Property Card.\n2. **Site Plan (1:200 or 1:500):** Indicating boundaries, access road width, adjoining survey numbers, and proposed setbacks.\n3. **Building Plans (1:100):** Floor plans, elevations, cross-sections, and drainage/septic layout signed by an authorized Architect/Engineer.\n4. **Structural Safety Certificate:** Signed by a qualified Structural Engineer in Form 3 as prescribed under Rule 21.\n5. **Supervision Certificate:** Undertaking in Form 4 by the Architect/Supervisor.",
      language: "en",
      citations: [
        {
          document_title: "MP Bhumi Vikas Niyam, 2012 (Administration & Procedures)",
          rule_number: "Rule 17 - Notice and Documents for Building Permission",
          page_number: 14,
          excerpt: "Every person who intends to erect or re-erect a building shall give notice in writing in Form 2 accompanied by site plan, building plans, services plan, ownership documents, and certificates prescribed under Rules 18 to 22.",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=14"
        },
        {
          document_title: "MP Bhumi Vikas Niyam, 2012",
          rule_number: "Rule 21 - Structural Design and Safety Certificate",
          page_number: 18,
          excerpt: "The application shall be accompanied by a structural safety certificate issued by a registered structural engineer certifying conformity with Indian Standard (IS) seismic and load codes.",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=18"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    },
    hi: {
      answer: "म.प्र. भूमि विकास नियम, 2012 के नियम 17 और नियम 21 के अनुसार भवन अनुज्ञा (प्रपत्र 2) हेतु आवश्यक दस्तावेज़:\n\n1. **स्वामित्व प्रमाण:** पंजीकृत विक्रय विलेख / पट्टा विलेख तथा नवीनतम खसरा/खतौनी/प्रॉपर्टी कार्ड।\n2. **साइट प्लान (1:200 या 1:500):** मार्ग चौड़ाई, सीमाएं, सेटबैक और भूखंड आयाम।\n3. **भवन मानचित्र (1:100):** फ्लोर प्लान, एलिवेशन, क्रॉस-सेक्शन एवं जल निकासी व्यवस्था, अधिकृत आर्किटेक्ट द्वारा हस्ताक्षरित।\n4. **संरचनात्मक सुरक्षा प्रमाण पत्र:** नियम 21 के तहत प्रपत्र 3 में पंजीकृत स्ट्रक्चरल इंजीनियर का प्रमाण पत्र।\n5. **पर्यवेक्षण प्रमाण पत्र:** प्रपत्र 4 में अधिकृत पर्यवेक्षक का वचनपत्र।",
      language: "hi",
      citations: [
        {
          document_title: "म.प्र. भूमि विकास नियम, 2012",
          rule_number: "नियम 17 एवं नियम 21 - भवन अनुज्ञा के दस्तावेज़ व सुरक्षा प्रमाण",
          page_number: 14,
          excerpt: "भवन निर्माण की सूचना प्रपत्र 2 में दी जाएगी जिसके साथ साइट प्लान, भवन नक्शे, स्वामित्व अभिलेख तथा प्रपत्र 3 में संरचनात्मक सुरक्षा प्रमाण पत्र संलग्न करना अनिवार्य है।",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=14"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    }
  },

  // 5. Parking requirements
  parking: {
    en: {
      answer: "Under Rule 84 and Schedule VII of the MP Bhumi Vikas Niyam, 2012, off-street parking standards for multi-family residential apartments are defined based on Equivalent Car Spaces (ECS):\n\n1. **Dwelling Units exceeding 150 sq.m carpet area:** 1 ECS per unit.\n2. **Dwelling Units between 75 sq.m and 150 sq.m:** 1 ECS for every 2 units.\n3. **Dwelling Units below 75 sq.m (LIG/EWS):** 1 ECS for every 4 units (or 2-wheeler equivalent).\n4. **Visitor Parking:** An additional **10% of total mandatory parking spaces** must be earmarked for visitors with unobstructed ground access.\n5. **Standard ECS Dimensions:** Minimum 2.5m x 5.0m for surface open parking, and 2.8m x 5.5m for stilt/basement parking.",
      language: "en",
      citations: [
        {
          document_title: "Madhya Pradesh Bhumi Vikas Niyam, 2012",
          rule_number: "Rule 84, Table No. 24 - Off-Street Parking Spaces",
          page_number: 88,
          excerpt: "Off-street parking space shall be provided for every building in accordance with Table 24. For multi-family dwellings, parking shall be calculated on the basis of carpet area per unit, with 10% extra space reserved exclusively for visitor parking.",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=88"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    },
    hi: {
      answer: "म.प्र. भूमि विकास नियम, 2012 के नियम 84 एवं तालिका 24 के अनुसार बहुमंजिला आवासीय अपार्टमेंट हेतु ऑफ-स्ट्रीट पार्किंग मानदंड:\n\n1. **150 वर्ग मीटर से अधिक कार्पेट क्षेत्र की इकाई:** 1 ECS (समकक्ष कार स्पेस) प्रति इकाई।\n2. **75 से 150 वर्ग मीटर कार्पेट क्षेत्र:** प्रत्येक 2 इकाइयों के लिए 1 ECS।\n3. **75 वर्ग मीटर से कम कार्पेट क्षेत्र:** प्रत्येक 4 इकाइयों के लिए 1 ECS।\n4. **आगंतुक (विज़िटर) पार्किंग:** कुल निर्धारित पार्किंग का **10% अतिरिक्त** स्थान आगंतुकों के लिए आरक्षित होना अनिवार्य है।\n5. **ECS आयाम:** खुले स्थान हेतु न्यूनतम 2.5m x 5.0m तथा स्टिल्ट/बेसमेंट हेतु 2.8m x 5.5m।",
      language: "hi",
      citations: [
        {
          document_title: "म.प्र. भूमि विकास नियम, 2012",
          rule_number: "नियम 84, तालिका 24 - ऑफ-स्ट्रीट पार्किंग विनिर्देश",
          page_number: 88,
          excerpt: "प्रत्येक बहुमंजिला आवासीय भवन हेतु तालिका 24 के अनुसार पार्किंग अनिवार्य है। कुल पार्किंग का 10 प्रतिशत अतिरिक्त भाग आगंतुक वाहनों के लिए आरक्षित रहेगा।",
          source_url: "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=88"
        }
      ],
      confidence: "high",
      insufficient_evidence: false,
      document_coverage_date: "2025-03-06"
    }
  },

  // 6. Insufficient evidence fallback (e.g., when asked about out of scope or unverified rules)
  insufficient: {
    en: {
      answer: "The regulatory repository does not contain sufficient verified statutory evidence under the Madhya Pradesh Bhumi Vikas Niyam, 2012 or current Gazette notifications to answer this query authoritatively.",
      language: "en",
      citations: [],
      confidence: "insufficient",
      insufficient_evidence: true,
      document_coverage_date: "2025-03-06"
    },
    hi: {
      answer: "मध्य प्रदेश भूमि विकास नियम, 2012 अथवा वर्तमान राजपत्रित अधिसूचनाओं की विनियामक रिपॉजिटरी में इस प्रश्न का आधिकारिक उत्तर देने के लिए पर्याप्त सत्यापित कानूनी साक्ष्य उपलब्ध नहीं हैं।",
      language: "hi",
      citations: [],
      confidence: "insufficient",
      insufficient_evidence: true,
      document_coverage_date: "2025-03-06"
    }
  }
};

/**
 * Helper to match query keywords to a realistic mock response
 */
export function getMockResponse(question, language = "en") {
  const q = question.toLowerCase();
  const lang = language === "hi" ? "hi" : "en";

  // Check for keywords triggering insufficient evidence
  if (
    q.includes("crypto") ||
    q.includes("bitcoin") ||
    q.includes("wheat") ||
    q.includes("subsidy") ||
    q.includes("fertilizer") ||
    q.includes("farm") ||
    q.includes("unknown") ||
    q.includes("insufficient") ||
    q.includes("nasa") ||
    q.includes("mars")
  ) {
    return mockResponses.insufficient[lang];
  }

  // Row housing
  if (q.includes("row") || q.includes("पंक्ति")) {
    return mockResponses.row_housing[lang];
  }

  // FAR / FSI / density
  if (q.includes("far") || q.includes("fsi") || q.includes("floor area") || q.includes("तल क्षेत्र")) {
    return mockResponses.far[lang];
  }

  // Permission / sanction / documents
  if (
    q.includes("permission") ||
    q.includes("document") ||
    q.includes("sanction") ||
    q.includes("अनुज्ञा") ||
    q.includes("दस्तावेज़") ||
    q.includes("certificate")
  ) {
    return mockResponses.permission[lang];
  }

  // Parking
  if (q.includes("parking") || q.includes("ecs") || q.includes("पार्किंग") || q.includes("गाड़ी")) {
    return mockResponses.parking[lang];
  }

  // Setback / open space / margin
  if (q.includes("setback") || q.includes("margin") || q.includes("सेटबैक") || q.includes("खुला स्थान")) {
    return mockResponses.setback[lang];
  }

  // Default to setback provision for general queries
  return mockResponses.setback[lang];
}
