/**
 * Display label for a citation's rule number.
 * The backend sends the rule as printed ("56", "26-B") or null when it is unknown;
 * mock data uses free-text labels ("Rule 52, Table No. 13"), which are shown as-is.
 */
export function formatRuleLabel(ruleNumber, language = 'en') {
  const value = ruleNumber === null || ruleNumber === undefined ? '' : String(ruleNumber).trim();
  if (!value) {
    return language === 'hi' ? 'नियम संख्या अज्ञात' : 'Rule not identified';
  }
  if (/^\d/.test(value)) {
    return language === 'hi' ? `नियम ${value}` : `Rule ${value}`;
  }
  return value;
}
