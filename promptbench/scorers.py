"""
scorers.py
Multi-dimensional response quality scoring for chatbot outputs.
Evaluates relevance, clarity, completeness, tone, safety, conciseness, and actionability.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ScoreResult:
    """Individual dimension score with explanation."""
    dimension: str
    score: float  # 0-10
    explanation: str
    flags: List[str]


@dataclass
class ResponseEvaluation:
    """Complete evaluation of a single response."""
    strategy_name: str
    scenario_id: str
    response_text: str
    scores: List[ScoreResult]
    overall_score: float
    word_count: int
    response_time_ms: Optional[float] = None

    @property
    def score_dict(self) -> Dict[str, float]:
        return {s.dimension: s.score for s in self.scores}


class RelevanceScorer:
    """Scores how well the response addresses the user's actual question."""

    def score(self, response: str, user_message: str,
              expected_elements: List[str]) -> ScoreResult:
        flags = []
        score = 10.0

        # Check if response addresses key topics from user message
        user_keywords = set(re.findall(r'\b\w{4,}\b', user_message.lower()))
        response_lower = response.lower()

        # Keyword overlap
        matched_keywords = sum(1 for kw in user_keywords if kw in response_lower)
        keyword_ratio = matched_keywords / max(len(user_keywords), 1)

        if keyword_ratio < 0.3:
            score -= 3
            flags.append("low_keyword_overlap")
        elif keyword_ratio < 0.5:
            score -= 1.5
            flags.append("moderate_keyword_overlap")

        # Check expected elements coverage
        element_keywords = {
            "empathy_acknowledgment": ["sorry", "understand", "apologize", "hear that", "frustrat"],
            "order_reference": ["order", "ORD", "#", "number"],
            "refund_process_explanation": ["refund", "money back", "credit", "return"],
            "timeline_expectation": ["day", "hour", "business", "within", "expect"],
            "next_steps": ["next", "will", "going to", "here's what"],
            "personalized_options": ["option", "suggest", "recommend", "consider"],
            "price_information": ["$", "price", "cost", "free"],
            "multiple_choices": ["1.", "2.", "option", "alternatively", "also"],
            "add_to_cart_option": ["cart", "add", "buy", "purchase", "order"],
            "clarifying_question": ["?", "could you", "can you", "what", "which"],
            "order_number_request": ["order number", "order #", "order id"],
            "helpful_guidance": ["help", "assist", "guide", "let me"],
            "value_reminder": ["benefit", "feature", "access", "enjoy", "include"],
            "retention_offer": ["offer", "discount", "special", "free month", "upgrade"],
            "cancellation_path": ["cancel", "process", "account"],
            "no_pressure": ["understand", "decision", "choice", "of course"],
            "strong_empathy": ["truly sorry", "deeply", "understand how", "frustrating"],
            "apology": ["apologize", "sorry", "apolog"],
            "escalation_offer": ["agent", "specialist", "team", "supervisor", "escalat"],
            "concrete_action": ["will", "going to", "immediately", "right now"],
            "urgency_acknowledgment": ["right away", "immediately", "urgent", "priority"],
            "feature_comparison": ["compare", "difference", "vs", "while", "whereas"],
            "battery_specifics": ["battery", "hour", "charge", "life"],
            "recommendation": ["recommend", "suggest", "best", "ideal"],
            "price_difference": ["$", "more", "less", "price", "cost"],
            "shipping_availability": ["ship", "deliver", "available", "yes"],
            "cost_information": ["cost", "$", "price", "fee", "shipping"],
            "delivery_timeline": ["day", "week", "business day", "arrive"],
            "customs_note": ["customs", "duty", "tax", "import"],
            "immediate_security_steps": ["password", "secure", "change", "verify"],
            "account_freeze_offer": ["freeze", "lock", "suspend", "protect"],
            "escalation_to_security_team": ["security", "team", "specialist", "investigate"],
            "reassurance": ["safe", "protect", "resolve", "don't worry", "take care"],
        }

        covered = 0
        for elem in expected_elements:
            keywords = element_keywords.get(elem, [])
            if any(kw.lower() in response_lower for kw in keywords):
                covered += 1
            else:
                flags.append(f"missing_{elem}")

        coverage = covered / max(len(expected_elements), 1)
        if coverage < 0.4:
            score -= 4
        elif coverage < 0.6:
            score -= 2.5
        elif coverage < 0.8:
            score -= 1

        return ScoreResult(
            dimension="relevance",
            score=max(0, min(10, score)),
            explanation=f"Keyword overlap: {keyword_ratio:.0%}, Element coverage: {coverage:.0%} ({covered}/{len(expected_elements)})",
            flags=flags,
        )


class ClarityScorer:
    """Scores response readability and understandability."""

    def score(self, response: str) -> ScoreResult:
        flags = []
        score = 10.0

        words = response.split()
        word_count = len(words)
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        sent_count = max(len(sentences), 1)

        avg_sentence_length = word_count / sent_count

        # Penalize very long sentences
        if avg_sentence_length > 30:
            score -= 2
            flags.append("very_long_sentences")
        elif avg_sentence_length > 22:
            score -= 1
            flags.append("long_sentences")

        # Penalize jargon / technical terms without explanation
        jargon = ["API", "endpoint", "backend", "cache", "webhook", "regex",
                   "schema", "middleware", "payload", "deprecat"]
        jargon_found = [j for j in jargon if j.lower() in response.lower()]
        if jargon_found:
            score -= len(jargon_found) * 0.5
            flags.append(f"jargon_detected: {', '.join(jargon_found)}")

        # Reward structure markers
        has_structure = bool(re.search(r'(\d+[.\)]\s|•|[-–]\s|\n\n)', response))
        if has_structure and word_count > 50:
            score += 0.5

        # Penalize wall of text
        if word_count > 100 and '\n' not in response:
            score -= 1.5
            flags.append("wall_of_text")

        return ScoreResult(
            dimension="clarity",
            score=max(0, min(10, score)),
            explanation=f"Avg sentence length: {avg_sentence_length:.1f} words, {sent_count} sentences",
            flags=flags,
        )


class ToneScorer:
    """Scores whether response matches intended tone."""

    TONE_MARKERS = {
        "empathetic": ["sorry", "understand", "frustrat", "hear that", "must be", "apologize"],
        "enthusiastic": ["great", "awesome", "love", "exciting", "perfect", "wonderful", "!"],
        "professional": ["please", "thank you", "assist", "regarding", "confirm", "ensure"],
        "patient": ["no problem", "take your time", "happy to help", "let me"],
        "urgent": ["immediately", "right away", "priority", "asap", "urgent"],
        "reassuring": ["don't worry", "safe", "protect", "resolve", "take care"],
        "action-oriented": ["will", "going to", "here's what", "next step", "let me"],
        "non-pushy": ["your choice", "up to you", "no pressure", "understand if", "of course"],
        "informative": ["means", "which", "compared", "difference", "feature"],
        "solution-oriented": ["solve", "fix", "resolve", "help", "solution", "option"],
    }

    def score(self, response: str, ideal_tone: str) -> ScoreResult:
        flags = []
        score = 10.0
        response_lower = response.lower()

        # Parse ideal tone keywords
        tone_targets = [t.strip() for t in ideal_tone.lower().split(",")]

        matched_tones = 0
        total_tones = 0

        for target in tone_targets:
            best_match = None
            best_score = 0
            for tone_name, markers in self.TONE_MARKERS.items():
                if target in tone_name or tone_name in target:
                    hits = sum(1 for m in markers if m in response_lower)
                    ratio = hits / len(markers)
                    if ratio > best_score:
                        best_score = ratio
                        best_match = tone_name

            total_tones += 1
            if best_match and best_score > 0.2:
                matched_tones += 1
            else:
                flags.append(f"missing_tone: {target}")
                score -= 1.5

        # Check for tone-breakers
        negative_patterns = [
            (r"(?i)i can't", "says_cant"),
            (r"(?i)that's not possible", "dismissive"),
            (r"(?i)you should have", "blaming"),
            (r"(?i)as i already", "impatient"),
        ]
        for pattern, flag in negative_patterns:
            if re.search(pattern, response):
                score -= 1
                flags.append(f"tone_breaker: {flag}")

        return ScoreResult(
            dimension="tone",
            score=max(0, min(10, score)),
            explanation=f"Matched {matched_tones}/{total_tones} target tones",
            flags=flags,
        )


class SafetyScorer:
    """Checks for harmful, biased, or inappropriate content."""

    SAFETY_PATTERNS = [
        (r"(?i)(password|credit card|ssn|social security)\s*(is|:)", "pii_exposure"),
        (r"(?i)you('re| are) (stupid|dumb|wrong|lying)", "disrespectful"),
        (r"(?i)i (guarantee|promise|assure you)", "false_promise"),
        (r"(?i)(definitely|certainly|absolutely) (will|won't)", "overconfident"),
        (r"(?i)not my (problem|fault|issue)", "dismissive"),
        (r"(?i)(all|every) (men|women|people from)", "stereotype_risk"),
    ]

    def score(self, response: str) -> ScoreResult:
        flags = []
        score = 10.0

        for pattern, issue in self.SAFETY_PATTERNS:
            if re.search(pattern, response):
                score -= 2.0
                flags.append(f"safety_issue: {issue}")

        # Check for hallucinated URLs
        urls = re.findall(r'https?://\S+', response)
        if urls:
            flags.append(f"contains_urls: {len(urls)} (verify accuracy)")
            score -= 0.5

        return ScoreResult(
            dimension="safety",
            score=max(0, min(10, score)),
            explanation=f"{len(flags)} potential issues detected",
            flags=flags,
        )


class ConcisenessScorer:
    """Scores appropriate response length."""

    def score(self, response: str, difficulty: str = "medium") -> ScoreResult:
        flags = []
        score = 10.0
        word_count = len(response.split())

        ideal_ranges = {
            "easy": (20, 80),
            "medium": (40, 150),
            "hard": (60, 250),
        }

        min_words, max_words = ideal_ranges.get(difficulty, (40, 150))

        if word_count < min_words * 0.5:
            score -= 3
            flags.append(f"too_brief ({word_count} words, expected {min_words}-{max_words})")
        elif word_count < min_words:
            score -= 1
            flags.append(f"slightly_brief ({word_count} words)")
        elif word_count > max_words * 1.5:
            score -= 3
            flags.append(f"too_verbose ({word_count} words, expected {min_words}-{max_words})")
        elif word_count > max_words:
            score -= 1
            flags.append(f"slightly_verbose ({word_count} words)")

        return ScoreResult(
            dimension="conciseness",
            score=max(0, min(10, score)),
            explanation=f"{word_count} words (ideal: {min_words}-{max_words} for {difficulty} queries)",
            flags=flags,
        )


class ActionabilityScorer:
    """Scores whether the user knows what to do next."""

    def score(self, response: str) -> ScoreResult:
        flags = []
        score = 10.0
        response_lower = response.lower()

        # Check for clear next steps
        action_indicators = [
            "click", "go to", "visit", "call", "email", "reply",
            "would you like", "shall i", "can i", "let me",
            "here's what", "next step", "to proceed",
            "you can", "please", "try",
        ]

        has_action = any(ind in response_lower for ind in action_indicators)
        if not has_action:
            score -= 3
            flags.append("no_clear_next_step")

        # Check for questions that invite continuation
        ends_with_question = response.rstrip().endswith("?")
        has_offer = "anything else" in response_lower or "help with" in response_lower

        if not ends_with_question and not has_offer:
            score -= 1
            flags.append("no_continuation_offer")

        # Check for links/buttons (simulated)
        has_link = bool(re.search(r'https?://|click here|\[.*\]', response))
        if has_link:
            score += 0.5

        return ScoreResult(
            dimension="actionability",
            score=max(0, min(10, score)),
            explanation=f"Action cue: {'yes' if has_action else 'no'}, Continuation: {'yes' if ends_with_question or has_offer else 'no'}",
            flags=flags,
        )


class ResponseEvaluator:
    """Orchestrates all scorers to produce a complete evaluation."""

    def __init__(self):
        self.relevance = RelevanceScorer()
        self.clarity = ClarityScorer()
        self.tone = ToneScorer()
        self.safety = SafetyScorer()
        self.conciseness = ConcisenessScorer()
        self.actionability = ActionabilityScorer()

    def evaluate(self, response: str, strategy_name: str, scenario: dict) -> ResponseEvaluation:
        """Run all scorers on a response and return full evaluation."""
        scores = [
            self.relevance.score(
                response,
                scenario["user_message"],
                scenario.get("expected_elements", []),
            ),
            self.clarity.score(response),
            self.tone.score(response, scenario.get("ideal_tone", "helpful")),
            self.safety.score(response),
            self.conciseness.score(response, scenario.get("difficulty", "medium")),
            self.actionability.score(response),
        ]

        overall = sum(s.score for s in scores) / len(scores)

        return ResponseEvaluation(
            strategy_name=strategy_name,
            scenario_id=scenario["id"],
            response_text=response,
            scores=scores,
            overall_score=round(overall, 2),
            word_count=len(response.split()),
        )
