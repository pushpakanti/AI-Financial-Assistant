"""Regression coverage for safe multi-turn conversational finance mutations."""

import unittest
from decimal import Decimal

from app.agents.finance_agent import _handle_mutation
from app.agents.planner_agent import planner_agent
from app.memory.memory_models import MemoryType


class FakeMemory:
    def __init__(self):
        self.records = {}
        self.next_id = 1

    def load_memory(self, user_id, memory_type=None, key=None):
        record = self.records.get((user_id, str(memory_type), key))
        return [record] if record and record.is_active else []

    def save_memory(self, user_id, memory_type, key, value):
        record = type("Record", (), {"id": self.next_id, "value": value, "is_active": True})()
        self.next_id += 1
        self.records[(user_id, str(memory_type), key)] = record
        return record

    def update_memory(self, user_id, memory_id, *, value=None, key=None):
        for record in self.records.values():
            if record.id == memory_id:
                record.value = value
                return record
        raise AssertionError("missing record")

    def delete_memory(self, user_id, memory_id):
        for record in self.records.values():
            if record.id == memory_id:
                record.is_active = False
                return
        raise AssertionError("missing record")


class FakeRegistry:
    def __init__(self, accounts=None):
        self.accounts = accounts or []
        self.withdrawals = []
        self.calls = []

    def execute(self, tool, user_id, action, payload):
        self.calls.append((tool, action))
        if (tool, action) == ("account", "list"):
            return {"success": True, "tool": tool, "action": action, "data": self.accounts}
        if (tool, action) == ("transaction", "withdraw"):
            self.withdrawals.append(payload)
            account = next(account for account in self.accounts if account["id"] == payload["account_id"])
            account["balance"] = str(Decimal(account["balance"]) - Decimal(payload["amount"]))
            return {"success": True, "tool": tool, "action": action, "data": {"id": len(self.withdrawals)}}
        if (tool, action) == ("budget", "summary"):
            return {
                "success": True,
                "tool": tool,
                "action": action,
                "data": {
                    "budget_count": 1,
                    "active_budget_count": 1,
                    "completed_budget_count": 0,
                    "expired_budget_count": 0,
                    "total_budgeted": "7000.00",
                    "total_spent": "0.00",
                    "total_remaining": "7000.00",
                },
            }
        if (tool, action) == ("transaction", "summary"):
            return {
                "success": True,
                "tool": tool,
                "action": action,
                "data": {
                    "transaction_count": 0,
                    "total_income": "0.00",
                    "total_expense": "0.00",
                    "total_transfer": "0.00",
                    "net_cash_flow": "0.00",
                },
            }
        if (tool, action) == ("dashboard", "get"):
            return {"success": True, "tool": tool, "action": action, "data": {"user_summary": {}}}
        if (tool, action) in (("transaction", "list"), ("transaction", "filter")):
            return {"success": True, "tool": tool, "action": action, "data": {"items": [], "total": 0}}
        raise AssertionError(f"Unexpected tool call: {tool}/{action}")


class ConversationalFinanceTests(unittest.TestCase):
    def setUp(self):
        self.account = {"id": 7, "name": "SBI Savings Updated", "account_type": "Savings", "balance": "55000.00", "currency": "INR"}
        self.memory = FakeMemory()
        self.registry = FakeRegistry([self.account])

    def state(self, request):
        return {"request": request, "user_id": 1, "memory_manager": self.memory, "tool_registry": self.registry}

    def test_withdrawal_requires_confirmation_then_executes_once(self):
        planned = planner_agent(self.state("Cut ₹10,000 from my savings account."))
        mutation = planned["mutation"]
        self.assertEqual(mutation["status"], "confirmation_required")
        self.assertEqual(mutation["operation"], "withdrawal")
        self.assertEqual(mutation["amount"], "10000")
        confirmation = _handle_mutation({**self.state("Cut ₹10,000 from my savings account."), "mutation": mutation, "planned_agents": ["finance"]}, mutation)
        self.assertIn("Should I proceed?", confirmation["finance_result"]["summary"])
        follow_up = planner_agent(self.state("yes"))["mutation"]
        completed = _handle_mutation({**self.state("yes"), "mutation": follow_up, "planned_agents": ["finance"]}, follow_up)
        self.assertIn("Withdrawal complete", completed["finance_result"]["summary"])
        self.assertEqual(len(self.registry.withdrawals), 1)
        self.assertEqual(self.registry.withdrawals[0]["account_id"], 7)
        self.assertEqual(self.registry.withdrawals[0]["transaction_type"], "EXPENSE")
        self.assertIsNone(planner_agent(self.state("yes")).get("mutation"))

    def test_cancelled_withdrawal_does_not_execute(self):
        mutation = planner_agent(self.state("Withdraw ₹10,000 from my savings account."))["mutation"]
        _handle_mutation({**self.state("request"), "mutation": mutation, "planned_agents": ["finance"]}, mutation)
        cancellation = planner_agent(self.state("no"))["mutation"]
        result = _handle_mutation({**self.state("no"), "mutation": cancellation, "planned_agents": ["finance"]}, cancellation)
        self.assertIn("No changes were made", result["finance_result"]["summary"])
        self.assertEqual(self.registry.withdrawals, [])

    def test_general_and_targeted_routing_do_not_invoke_tools(self):
        for message in ("Hello", "Who are you?"):
            result = planner_agent(self.state(message))
            self.assertEqual(result["planned_agents"], [])
            self.assertEqual(result["tool_results"], [])
        self.assertEqual(self.registry.calls, [])
        self.assertEqual(planner_agent(self.state("Show my goals"))["planned_agents"], ["goal"])
        self.assertEqual(planner_agent(self.state("How much have I spent and how much budget is left?"))["planned_agents"], ["finance", "budget"])
        self.assertEqual(
            self.registry.calls,
            [("budget", "summary"), ("transaction", "summary"), ("dashboard", "get")],
        )
        self.assertEqual(planner_agent(self.state("Analyze my dashboard and goals"))["planned_agents"], ["goal", "report"])

    def test_investment_and_planning_routing(self):
        for message in (
            "I have invested 7000 in stocks",
            "Give me a financial plan",
            "I want an investment plan for September",
        ):
            result = planner_agent(self.state(message))
            self.assertIn("finance", result["planned_agents"])

    def test_pending_account_clarification_resolves_alias_then_confirms_and_executes(self):
        initial = planner_agent(self.state("debit ₹15,000 from this account"))["mutation"]
        self.assertEqual(initial["status"], "clarification_required")
        self.assertEqual(initial["operation"], "withdrawal")
        self.assertEqual(initial["amount"], "15000")
        clarification = _handle_mutation({**self.state("debit ₹15,000 from this account"), "mutation": initial, "planned_agents": ["finance"]}, initial)
        self.assertIn("Which account", clarification["finance_result"]["summary"])
        stored = self.memory.load_memory(1, MemoryType.CONVERSATION, "pending_financial_operation")
        self.assertEqual(stored[0].value["account"], None)
        self.assertEqual(stored[0].value["user_id"], 1)

        resolved = planner_agent(self.state("SBI"))["mutation"]
        self.assertEqual(resolved["status"], "confirmation_required")
        self.assertEqual(resolved["account"]["name"], "SBI Savings Updated")
        confirmed = _handle_mutation({**self.state("SBI"), "mutation": resolved, "planned_agents": ["finance"]}, resolved)
        self.assertIn("Should I proceed?", confirmed["finance_result"]["summary"])

        accepted = planner_agent(self.state("yes"))["mutation"]
        _handle_mutation({**self.state("yes"), "mutation": accepted, "planned_agents": ["finance"]}, accepted)
        self.assertEqual(len(self.registry.withdrawals), 1)
        self.assertEqual(self.registry.withdrawals[0]["amount"], "15000")
        self.assertEqual(self.account["balance"], "40000.00")

    def test_cancel_after_account_clarification_clears_pending_without_mutation(self):
        initial = planner_agent(self.state("debit ₹15,000 from this account"))["mutation"]
        _handle_mutation({**self.state("debit ₹15,000 from this account"), "mutation": initial, "planned_agents": ["finance"]}, initial)
        resolved = planner_agent(self.state("SBI"))["mutation"]
        _handle_mutation({**self.state("SBI"), "mutation": resolved, "planned_agents": ["finance"]}, resolved)
        cancelled = planner_agent(self.state("no"))["mutation"]
        _handle_mutation({**self.state("no"), "mutation": cancelled, "planned_agents": ["finance"]}, cancelled)
        self.assertEqual(self.registry.withdrawals, [])
        self.assertIsNone(planner_agent(self.state("yes")).get("mutation"))

    def test_ambiguous_account_and_memory_question_stay_safe(self):
        self.registry.accounts = [
            {**self.account, "name": "SBI Savings"},
            {**self.account, "id": 8, "name": "SBI Current", "account_type": "Current"},
        ]
        mutation = planner_agent(self.state("debit ₹15,000 from this account"))["mutation"]
        self.assertEqual(mutation["status"], "clarification_required")
        _handle_mutation({**self.state("debit ₹15,000 from this account"), "mutation": mutation, "planned_agents": ["finance"]}, mutation)
        ambiguous = planner_agent(self.state("SBI"))["mutation"]
        self.assertEqual(ambiguous["status"], "clarification_required")
        self.assertIsNone(ambiguous["account"])
        memory = planner_agent(self.state("Do you have memory?"))
        self.assertEqual(memory["planned_agents"], [])
        self.assertEqual(memory["tool_results"], [])
        self.assertIn("conversation context", memory["planner_result"]["data"]["general_response"])

    def test_past_tense_expense_is_not_claimed_as_recorded_until_confirmed(self):
        mutation = planner_agent(self.state("I spent ₹10,000 at the shopping mall."))["mutation"]
        self.assertEqual(mutation["operation"], "expense")
        self.assertEqual(mutation["merchant"], "shopping mall")
        response = _handle_mutation({**self.state("I spent ₹10,000 at the shopping mall."), "mutation": mutation, "planned_agents": ["finance"]}, mutation)
        self.assertIn("Should I proceed?", response["finance_result"]["summary"])
        self.assertEqual(self.registry.withdrawals, [])

    def test_unresolved_past_tense_expense_never_claims_recording(self):
        self.registry.accounts.append({**self.account, "id": 8, "name": "ICICI Savings"})
        mutation = planner_agent(self.state("I spent ₹10,000 at the shopping mall."))["mutation"]
        response = _handle_mutation({**self.state("I spent ₹10,000 at the shopping mall."), "mutation": mutation, "planned_agents": ["finance"]}, mutation)
        self.assertIn("haven't recorded", response["finance_result"]["summary"])
        self.assertEqual(self.registry.withdrawals, [])

    def test_llm_gateway_provider_selection(self):
        from app.ai import LLMGateway
        gateway = LLMGateway()
        
        # Test Gemini selection for complex reasoning markers
        self.assertEqual(gateway._preferred_provider_name("Analyze my spending"), "gemini")
        self.assertEqual(gateway._preferred_provider_name("Give me a financial plan"), "gemini")
        self.assertEqual(gateway._preferred_provider_name("I have invested 7000 in stocks"), "gemini")
        
        # Test Groq selection for simple lookups
        self.assertEqual(gateway._preferred_provider_name("What is my balance?"), "groq")
        self.assertEqual(gateway._preferred_provider_name("Show my transactions"), "groq")

    def test_affordability_and_general_intents(self):
        # 1. "Can I afford ₹10,000 this month?"
        state_1 = self.state("Can I afford ₹10,000 this month?")
        planned_1 = planner_agent(state_1)
        self.assertIn("finance", planned_1["planned_agents"])

        # 2. "Do I have enough money for ₹5,000?"
        state_2 = self.state("Do I have enough money for ₹5,000?")
        planned_2 = planner_agent(state_2)
        self.assertIn("finance", planned_2["planned_agents"])

        # 3. "Can I afford this purchase?" (Finance agent selected, asks for amount)
        state_3 = self.state("Can I afford this purchase?")
        planned_3 = planner_agent(state_3)
        self.assertIn("finance", planned_3["planned_agents"])
        
        # Now execute the finance agent with planned agents set
        # Since no LLM is running here, it will use deterministic fallback.
        from app.agents.finance_agent import finance_agent
        res_3 = finance_agent({**state_3, "planned_agents": planned_3["planned_agents"]})
        self.assertIn("please tell me the amount", res_3["finance_result"]["summary"])

        # 4. "What are my biggest expenses this month?"
        state_4 = self.state("What are my biggest expenses this month?")
        planned_4 = planner_agent(state_4)
        self.assertIn("finance", planned_4["planned_agents"])

        # 5. "What is my budget remaining?"
        state_5 = self.state("What is my budget remaining?")
        planned_5 = planner_agent(state_5)
        self.assertIn("budget", planned_5["planned_agents"])

        # 6. "What are my savings goals?"
        state_6 = self.state("What are my savings goals?")
        planned_6 = planner_agent(state_6)
        self.assertIn("goal", planned_6["planned_agents"])

        # 7. "Give me a financial report."
        state_7 = self.state("Give me a financial report.")
        planned_7 = planner_agent(state_7)
        self.assertIn("report", planned_7["planned_agents"])

        # 8. "Hello"
        state_8 = self.state("Hello")
        planned_8 = planner_agent(state_8)
        self.assertEqual(planned_8["planned_agents"], [])


if __name__ == "__main__":
    unittest.main()
