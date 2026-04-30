"""
promptbench.py
Main evaluation engine for prompt strategy A/B testing.
Runs test scenarios against multiple prompt strategies and produces comparative reports.

Usage:
    # With simulated responses (demo mode):
    python promptbench.py --strategies configs/prompt_strategies.yaml \
                          --scenarios configs/test_scenarios.yaml \
                          --output outputs/ --mode demo

    # With OpenAI API:
    python promptbench.py --strategies configs/prompt_strategies.yaml \
                          --scenarios configs/test_scenarios.yaml \
                          --output outputs/ --mode openai --api-key YOUR_KEY

    # With saved responses:
    python promptbench.py --scenarios configs/test_scenarios.yaml \
                          --responses data/sample_responses.json \
                          --output outputs/ --mode offline
"""

import json
import argparse
import time
from typing import List, Dict, Optional
from pathlib import Path

import yaml

from scorers import ResponseEvaluator, ResponseEvaluation
from report_generator import generate_comparison_report


# ---------------------------------------------------------------------------
# Simulated LLM responses for demo mode (no API key needed)
# ---------------------------------------------------------------------------

DEMO_RESPONSES = {
    "concise_direct": {
        "refund_broken_item": "I can see order #ORD-45231. Since the item arrived broken, you're eligible for a full refund. I've initiated the process — expect the refund in 3-5 business days. Is there anything else?",
        "product_recommendation": "For a gardening/cooking mom around $50, I'd suggest: Herb Garden Starter Kit ($34.99) or Premium Garden Tool Set ($47.99). Want me to add either to your cart?",
        "order_tracking_vague": "I'd be happy to help track your order. Could you share your order number? You can find it in your confirmation email.",
        "cancellation_retention": "I understand you want to cancel Premium. Before I process that, you currently get free shipping and 10% off all orders. Would you like to proceed with cancellation, or would a 3-month discount help?",
        "complaint_escalation": "I sincerely apologize for the repeated issues. This is unacceptable. I'm escalating your case to a senior agent right now with priority status. You'll hear back within 2 hours. Reference: ESC-8827.",
        "comparison_shopping": "Standard Earbuds: 6hr battery, $49.99. Pro Earbuds: 10hr battery with ANC, $89.99. For battery life, the Pro is the clear winner. Want details on either?",
        "international_shipping": "Yes, we ship to Brazil. Standard shipping: $14.99, 10-15 business days. Express: $29.99, 5-7 days. Note: customs duties may apply at delivery and vary by item value.",
        "account_security": "I'm treating this as urgent. Please change your password immediately at shopease.com/security. I'm flagging your account for review and connecting you with our security team now. Don't worry — unauthorized charges will be reversed.",
    },
    "friendly_detailed": {
        "refund_broken_item": "Oh no, I'm so sorry to hear your item arrived broken! 😟 That's really frustrating, and I completely understand why you'd want a refund.\n\nI've pulled up your order #ORD-45231, and I can see the details. Since the item was damaged on arrival, you're absolutely eligible for a full refund. Here's what will happen:\n\n1. I'm initiating your refund right now\n2. You'll receive a confirmation email within the hour\n3. The refund will appear on your original payment method in 3-5 business days\n4. No need to return the broken item!\n\nIs there anything else I can help you with? I'd love to make sure your next experience with us is a great one! 😊",
        "product_recommendation": "What a lovely idea — shopping for your mom's birthday! 🎂 Since she loves gardening and cooking, I have some great options around your $50 budget:\n\n🌱 **Herb Garden Starter Kit** - $34.99\nIncludes 6 herb varieties, pots, and soil. Perfect for a kitchen garden!\n\n🔪 **Artisan Kitchen Herb Scissors Set** - $24.99\nBeautifully designed scissors for fresh herbs, with a magnetic holder.\n\n🌿 **Garden-to-Table Gift Box** - $49.99\nCombines a mini herb planter with a recipe book and gourmet seasoning set. This one's our bestseller for gardener-cooks!\n\nI think the Garden-to-Table Gift Box would be perfect since it combines both her passions! Would you like me to add it to your cart with gift wrapping? 🎁",
        "order_tracking_vague": "Hey there! I'd love to help you find out where your order is! 📦\n\nCould you share your order number with me? You can usually find it in:\n- Your confirmation email (subject line starting with \"Order Confirmed\")\n- Your account under \"My Orders\" at shopease.com/orders\n\nOnce I have that, I'll get you real-time tracking info right away!",
        "cancellation_retention": "I hear you, and I'm sorry that Premium hasn't felt worth it for you. That's important feedback.\n\nBefore I process the cancellation, I wanted to make sure you know what you've been getting:\n- Free shipping on all orders (you've saved $47 in shipping this year!)\n- 10% off every purchase\n- Early access to sales\n\nI'd hate for you to lose those benefits. Would any of these help?\n- **50% off your next 3 months** — so you can reassess at a lower cost\n- **Downgrade to Basic** — keeps free shipping at a lower price\n\nOf course, if you'd still like to cancel, I completely respect that and can process it right now. What would you prefer? 😊",
        "complaint_escalation": "I am truly, deeply sorry about this experience. Being contacted three times for the same issue is absolutely not okay, and I completely understand your frustration. You deserve so much better than this.\n\nHere's what I'm doing right now:\n1. 🚨 Escalating your case to a senior specialist with PRIORITY status\n2. 📋 Documenting your full history so you won't have to repeat yourself\n3. 📞 A specialist will reach out to you within 2 hours maximum\n\nYour reference number is ESC-8827. I'm also flagging this internally so we can improve. You shouldn't have had to reach out three times, and I'm sorry. Is there anything else I can do for you right now?",
        "comparison_shopping": "Great question! Let me break down the differences for you:\n\n🎧 **Standard Wireless Earbuds** - $49.99\n- Battery: 6 hours (+ 18hrs with case)\n- Sound: High-quality stereo\n- Water resistance: IPX4 (sweat-proof)\n- Perfect for: Casual listening, commutes\n\n🎧 **Pro Wireless Earbuds** - $89.99\n- Battery: 10 hours (+ 30hrs with case) ⚡\n- Sound: Premium drivers + Active Noise Cancellation\n- Water resistance: IPX5 (rain-proof)\n- Perfect for: Workouts, travel, focus time\n\nFor **battery life specifically**, the Pro is the clear winner — nearly double the playtime! If that's your priority, the extra $40 is well worth it.\n\nWould you like me to add either to your cart? 😊",
        "international_shipping": "Great news — yes, we absolutely ship to Brazil! 🇧🇷\n\nHere are your shipping options:\n\n📦 **Standard International** - $14.99\n- Delivery: 10-15 business days\n- Tracking included\n\n✈️ **Express International** - $29.99\n- Delivery: 5-7 business days\n- Priority tracking + insurance\n\n💡 **Good to know about customs:**\nBrazil may charge import duties on international packages. These are collected at delivery and depend on your order value. For orders under $50 USD, duties are typically minimal.\n\nWould you like help finding something specific, or shall I help you place an order?",
        "account_security": "I can see why you're alarmed — unauthorized purchases are very concerning, and I want you to know we take this extremely seriously. Let's secure your account right away.\n\n🔒 **Immediate steps:**\n1. Please change your password NOW: shopease.com/security\n2. I'm temporarily freezing your account to prevent further unauthorized activity\n3. I'm flagging all recent purchases for review\n\n🛡️ **What happens next:**\n- Our security team will investigate within 24 hours\n- Any confirmed unauthorized charges will be fully reversed\n- You'll receive an email with a detailed report\n\nYour reference number is SEC-2026-1847. Don't worry — we'll get this sorted out and make sure your account is protected. Would you like me to connect you with our security specialist right now?",
    },
    "structured_professional": {
        "refund_broken_item": "Thank you for contacting us regarding order #ORD-45231.\n\n**Issue:** Item received in damaged condition.\n\n**Resolution:** Full refund approved. As the item arrived defective, no return is required.\n\n**Timeline:**\n- Refund initiated: Today\n- Confirmation email: Within 1 hour\n- Refund credited: 3-5 business days to original payment method\n\nPlease retain the item for 48 hours in case our quality team requests photos for our records. If you would like a replacement instead, please let me know.",
        "product_recommendation": "Based on your criteria (recipient: mother, interests: gardening + cooking, budget: ~$50), I recommend the following options:\n\n**Option 1: Garden-to-Table Gift Box — $49.99**\nIncludes herb planter, recipe book, and gourmet seasonings. Highly rated (4.8/5).\n\n**Option 2: Herb Garden Starter Kit — $34.99**\n6 herb varieties with pots and organic soil. Leaves room in budget for an add-on.\n\n**Option 3: Premium Garden Tool Set — $47.99**\nErgonomic 8-piece set with carrying case. Best seller in garden category.\n\nGift wrapping is available at no additional charge for all options. Would you like to proceed with any of these selections?",
        "order_tracking_vague": "I would be happy to help you locate your order.\n\nTo pull up your tracking information, I will need your order number. You can find this in:\n1. Your order confirmation email (subject: \"Order Confirmed\")\n2. Your account dashboard under \"Order History\"\n\nPlease provide the order number and I will retrieve the current status for you.",
        "cancellation_retention": "I understand you wish to cancel your ShopEase Premium membership.\n\n**Current Benefits Summary:**\n- Free shipping on all orders (total savings to date: $47.00)\n- 10% discount on all purchases\n- Early access to seasonal sales\n\n**Available Alternatives:**\n1. 50% discount for the next 3 billing cycles\n2. Downgrade to Basic plan ($4.99/mo) — retains free shipping benefit\n\n**To proceed with cancellation:**\nI can process this immediately. Your benefits will remain active until the end of your current billing period (April 15, 2026).\n\nPlease confirm your preferred option.",
        "complaint_escalation": "I sincerely apologize for the repeated inconvenience. This level of service is below our standards, and I take full responsibility on behalf of our team.\n\n**Immediate Actions Taken:**\n1. Case escalated to Senior Resolution Team — Priority Level: HIGH\n2. Full case history compiled (3 prior contacts documented)\n3. Assigned to dedicated agent to prevent further transfers\n\n**Expected Resolution:**\n- Senior agent contact within 2 hours\n- You will not need to re-explain your issue\n- Reference number: ESC-8827\n\nI have also flagged this case for our quality assurance review. Is there anything additional you would like documented for the escalation?",
        "comparison_shopping": "Here is a detailed comparison of the two models:\n\n| Feature | Standard | Pro |\n|---------|----------|-----|\n| Price | $49.99 | $89.99 |\n| Battery Life | 6 hrs (18 w/ case) | 10 hrs (30 w/ case) |\n| Noise Cancellation | No | Active (ANC) |\n| Water Resistance | IPX4 | IPX5 |\n| Driver Size | 10mm | 12mm |\n\n**Battery Verdict:** The Pro offers 67% more battery life per charge.\n\n**Recommendation:** For users prioritizing battery life, the Pro model provides significantly better value per charge cycle.\n\nWould you like to add either model to your cart?",
        "international_shipping": "Confirmed: We ship to Brazil.\n\n**Shipping Options to Brazil:**\n\n| Method | Cost | Delivery | Tracking |\n|--------|------|----------|----------|\n| Standard | $14.99 | 10-15 business days | Basic |\n| Express | $29.99 | 5-7 business days | Priority + Insurance |\n\n**Customs & Duties:**\nBrazilian customs may assess import duties upon delivery. Rates vary by product category and declared value. ShopEase is not responsible for local customs charges.\n\n**Free Shipping:** Available on orders exceeding $100 USD (Standard method).\n\nWould you like assistance placing an order?",
        "account_security": "This has been flagged as a **HIGH PRIORITY** security incident.\n\n**Immediate Required Actions:**\n1. Change your password now: shopease.com/account/security\n2. Enable two-factor authentication if not already active\n3. Review recent login activity at shopease.com/account/sessions\n\n**Actions Taken on Our End:**\n- Account flagged for security review\n- Suspicious transactions frozen pending investigation\n- Security team notified — investigation begins within 24 hours\n\n**Regarding Unauthorized Charges:**\nAll confirmed unauthorized transactions will be fully reversed. You will receive a detailed report via email.\n\n**Reference:** SEC-2026-1847\n\nWould you like to be connected with our security team directly?",
    },
}


# ---------------------------------------------------------------------------
# LLM API integration (pluggable)
# ---------------------------------------------------------------------------

def get_llm_response(system_prompt: str, user_message: str,
                     temperature: float = 0.5, max_tokens: int = 300,
                     mode: str = "demo", api_key: str = None,
                     strategy_name: str = "", scenario_id: str = "") -> str:
    """Get response from LLM. Supports demo mode and OpenAI API."""

    if mode == "demo":
        return DEMO_RESPONSES.get(strategy_name, {}).get(
            scenario_id,
            "I'd be happy to help you with that. Could you provide more details?"
        )

    elif mode == "openai":
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except ImportError:
            print("openai package not installed. Run: pip install openai")
            return ""
        except Exception as e:
            print(f"API error: {e}")
            return ""

    return ""


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_evaluation(
    strategies_path: str,
    scenarios_path: str,
    output_dir: str = "outputs",
    mode: str = "demo",
    api_key: str = None,
    responses_path: str = None,
):
    """Run the complete prompt evaluation pipeline."""

    # Load configs
    with open(strategies_path, "r") as f:
        strategies_config = yaml.safe_load(f)
    with open(scenarios_path, "r") as f:
        scenarios_config = yaml.safe_load(f)

    strategies = strategies_config["strategies"]
    scenarios = scenarios_config["scenarios"]

    # Load pre-saved responses if in offline mode
    saved_responses = {}
    if mode == "offline" and responses_path:
        with open(responses_path, "r") as f:
            saved_responses = json.load(f)

    evaluator = ResponseEvaluator()
    all_evaluations: Dict[str, List[ResponseEvaluation]] = {}
    all_responses = {}  # For saving

    print("=" * 60)
    print("PromptBench — Prompt Strategy Evaluation")
    print("=" * 60)
    print(f"Strategies: {len(strategies)}")
    print(f"Scenarios:  {len(scenarios)}")
    print(f"Mode:       {mode}")
    print(f"Total runs: {len(strategies) * len(scenarios)}")
    print("=" * 60)

    for strat_key, strat_config in strategies.items():
        print(f"\n▶ Strategy: {strat_config.get('name', strat_key)}")
        all_evaluations[strat_key] = []
        all_responses[strat_key] = {}

        for scenario in scenarios:
            sid = scenario["id"]

            # Get response
            if mode == "offline" and strat_key in saved_responses:
                response = saved_responses[strat_key].get(sid, "")
            else:
                response = get_llm_response(
                    system_prompt=strat_config["system_prompt"],
                    user_message=scenario["user_message"],
                    temperature=strat_config.get("temperature", 0.5),
                    max_tokens=strat_config.get("max_tokens", 300),
                    mode=mode,
                    api_key=api_key,
                    strategy_name=strat_key,
                    scenario_id=sid,
                )

            all_responses[strat_key][sid] = response

            # Evaluate
            evaluation = evaluator.evaluate(response, strat_key, scenario)
            all_evaluations[strat_key].append(evaluation)

            print(f"  ✓ {sid:30s} → {evaluation.overall_score:.1f}/10")

    # Generate report
    print("\n" + "=" * 60)
    print("Generating comparison report...")
    report = generate_comparison_report(all_evaluations, output_dir)

    # Save responses for reuse
    responses_out = Path(output_dir) / "generated_responses.json"
    with open(responses_out, "w") as f:
        json.dump(all_responses, f, indent=2)
    print(f"Responses saved to {responses_out}")

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    for strat_key, evals in all_evaluations.items():
        avg = sum(e.overall_score for e in evals) / len(evals) if evals else 0
        print(f"  {strat_key:30s} → Avg: {avg:.1f}/10")

    best = max(all_evaluations.items(), key=lambda x: sum(e.overall_score for e in x[1]) / len(x[1]))
    print(f"\n  🏆 Winner: {best[0]}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="PromptBench — Prompt Strategy Evaluator")
    parser.add_argument("--strategies", "-s", required=True, help="Path to prompt strategies YAML")
    parser.add_argument("--scenarios", "-t", required=True, help="Path to test scenarios YAML")
    parser.add_argument("--output", "-o", default="outputs", help="Output directory")
    parser.add_argument("--mode", "-m", default="demo", choices=["demo", "openai", "offline"],
                        help="Execution mode: demo (simulated), openai (API), offline (pre-saved)")
    parser.add_argument("--api-key", help="API key for LLM provider")
    parser.add_argument("--responses", help="Path to pre-saved responses JSON (for offline mode)")
    args = parser.parse_args()

    run_evaluation(
        strategies_path=args.strategies,
        scenarios_path=args.scenarios,
        output_dir=args.output,
        mode=args.mode,
        api_key=args.api_key,
        responses_path=args.responses,
    )


if __name__ == "__main__":
    main()
