# PromptBench ⚡

**A systematic prompt engineering evaluation framework for optimizing chatbot response quality, consistency, and task alignment.**

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

PromptBench provides a structured methodology for designing, testing, and comparing prompt strategies used in LLM-powered chatbots. Instead of ad-hoc prompt tweaking, PromptBench treats prompt engineering as a measurable optimization problem — running controlled experiments across prompt variants and scoring responses on multiple quality dimensions.

### Why PromptBench?

Conversation designers iterate on prompts constantly but rarely have a systematic way to:
- Compare which prompt phrasing produces better responses
- Measure response quality beyond "does it sound right?"
- Track prompt performance over time as models update
- Share reusable prompt patterns across teams

PromptBench solves this with automated A/B testing of prompt strategies, multi-dimensional scoring, and exportable comparison reports.

### Key Features

- **Prompt Strategy Library**: Define and version prompt templates with variable slots
- **Automated A/B Testing**: Run identical queries against multiple prompt variants
- **Multi-Dimensional Scoring**: Rate responses on relevance, clarity, completeness, tone, safety
- **Response Consistency Check**: Detect when the same prompt produces wildly different outputs
- **Comparative Reports**: Side-by-side Markdown/HTML reports with winner analysis
- **Model-Agnostic**: Works with any LLM API (OpenAI, Anthropic, local models)

## Architecture

```
Test Scenarios (YAML)
        │
        ▼
┌───────────────────┐
│ Prompt Strategy    │  ← prompt_v1.yaml, prompt_v2.yaml
│ Definitions        │
└────────┬──────────┘
         │
    ┌────▼──────────┐
    │ Evaluation     │──► Relevance Scorer
    │ Engine         │──► Clarity Scorer  
    │                │──► Completeness Scorer
    │                │──► Tone Analyzer
    │                │──► Safety Checker
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Comparison     │──► A/B Report (Markdown)
    │ Report Engine  │──► Score Matrices
    │                │──► Winner Summary
    └───────────────┘
```

## Installation

```bash
git clone https://github.com/yourusername/promptbench.git
cd promptbench
pip install -r requirements.txt
```

## Quick Start

### 1. Define Prompt Strategies

```yaml
# configs/prompt_strategies.yaml
strategies:
  concise_direct:
    system_prompt: |
      You are a helpful e-commerce customer service agent.
      Be concise. Answer in 1-2 sentences max.
      If you can't help, say so immediately.
    temperature: 0.3
    
  friendly_detailed:
    system_prompt: |
      You are a warm, friendly customer service agent for an online store.
      Show empathy first, then provide detailed help.
      Always offer additional assistance.
    temperature: 0.7
```

### 2. Define Test Scenarios

```yaml
# configs/test_scenarios.yaml
scenarios:
  - id: refund_request
    user_message: "I want a refund for order #12345, the item arrived broken"
    expected_elements: ["empathy", "order_lookup", "refund_process", "timeline"]
    category: "support"
    
  - id: product_recommendation
    user_message: "I need a birthday gift for my mom, she likes gardening"
    expected_elements: ["options", "price_range", "personalization"]
    category: "sales"
```

### 3. Run Evaluation

```bash
python promptbench.py --strategies configs/prompt_strategies.yaml \
                      --scenarios configs/test_scenarios.yaml \
                      --output outputs/
```

## Scoring Dimensions

| Dimension | What It Measures | Scale |
|-----------|-----------------|-------|
| **Relevance** | Does the response address the user's actual question? | 0-10 |
| **Clarity** | Is the response easy to understand? | 0-10 |
| **Completeness** | Does it cover all expected elements? | 0-10 |
| **Tone** | Does it match the intended brand voice? | 0-10 |
| **Safety** | Free from harmful, biased, or inappropriate content? | 0-10 |
| **Conciseness** | Appropriate length — not too verbose, not too sparse? | 0-10 |
| **Actionability** | Does the user know what to do next? | 0-10 |

## Sample Report Output

```
╔══════════════════════════════════════════════════════════╗
║            PROMPT STRATEGY COMPARISON REPORT            ║
╠══════════════════════════════════════════════════════════╣
║ Scenario: refund_request                                ║
║                                                         ║
║ Strategy A: concise_direct       Score: 7.2/10          ║
║ Strategy B: friendly_detailed    Score: 8.6/10  ★       ║
║                                                         ║
║ Winner: friendly_detailed (+1.4)                        ║
║ Key diff: +2.1 on empathy, -0.7 on conciseness         ║
╠══════════════════════════════════════════════════════════╣
║ Scenario: product_recommendation                        ║
║                                                         ║
║ Strategy A: concise_direct       Score: 6.8/10          ║
║ Strategy B: friendly_detailed    Score: 9.1/10  ★       ║
║                                                         ║
║ Winner: friendly_detailed (+2.3)                        ║
║ Key diff: +3.0 on personalization, -0.2 on clarity      ║
╚══════════════════════════════════════════════════════════╝
```

## Project Structure

```
promptbench/
├── promptbench.py           # Main evaluation engine
├── scorers.py               # Response quality scoring modules
├── report_generator.py      # Comparison report builder
├── requirements.txt
├── configs/
│   ├── prompt_strategies.yaml
│   └── test_scenarios.yaml
├── data/
│   └── sample_responses.json
└── outputs/
    ├── comparison_report.md
    └── score_matrix.json
```

## Use Cases for Conversation Designers

1. **Prompt Iteration**: Compare v1 vs v2 of a system prompt systematically
2. **Tone Calibration**: Find the right balance between friendly and efficient
3. **Edge Case Testing**: Evaluate how prompts handle tricky user inputs
4. **Cross-Model Comparison**: Test same prompts across GPT-4, Claude, etc.
5. **Regression Testing**: Ensure prompt changes don't degrade existing quality
6. **Team Alignment**: Share scored examples as "what good looks like" references

## License

MIT License
