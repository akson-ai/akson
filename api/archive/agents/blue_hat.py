import random
import time
from enum import Enum
from typing import Any, Dict, List


class HatColor(Enum):
    WHITE = "White"
    RED = "Red"
    BLACK = "Black"
    YELLOW = "Yellow"
    GREEN = "Green"
    BLUE = "Blue"


class BlueHatOrchestrator:
    def __init__(self):
        self.current_hat = None
        self.agenda: List[HatColor] = []
        self.insights: Dict[HatColor, Any] = {}
        self.shared_context: Dict[str, Any] = {}
        self.start_time: float

    def set_initial_agenda(self, problem_type: str):
        if problem_type == "creative":
            self.agenda = [HatColor.WHITE, HatColor.GREEN, HatColor.YELLOW, HatColor.BLACK, HatColor.RED]
        elif problem_type == "critical":
            self.agenda = [HatColor.WHITE, HatColor.BLACK, HatColor.YELLOW, HatColor.RED, HatColor.GREEN]
        elif problem_type == "emotional":
            self.agenda = [HatColor.RED, HatColor.WHITE, HatColor.YELLOW, HatColor.BLACK, HatColor.GREEN]
        else:  # default
            self.agenda = [HatColor.WHITE, HatColor.RED, HatColor.YELLOW, HatColor.BLACK, HatColor.GREEN]

        print("Initial agenda set:", [hat.value for hat in self.agenda])

    def adjust_agenda(self):
        adjustments_made = False

        # 1. Handle high emotional content
        if HatColor.RED in self.insights and "high_emotion" in self.insights[HatColor.RED]:
            if HatColor.RED not in self.agenda[:2]:  # If RED is not in the next two steps
                self.agenda.insert(0, HatColor.RED)  # Prioritize emotional consideration
                adjustments_made = True

        # 2. Address major obstacles
        if HatColor.BLACK in self.insights and "major_obstacle" in self.insights[HatColor.BLACK]:
            if HatColor.GREEN not in self.agenda:  # If GREEN is not already in the agenda
                self.agenda.append(HatColor.GREEN)  # Add another creative thinking session
                adjustments_made = True

        # 3. Fact-check if there's uncertainty
        if any("uncertain" in str(insight).lower() for insight in self.insights.values()):
            if HatColor.WHITE not in self.agenda:
                self.agenda.insert(1, HatColor.WHITE)  # Add fact-checking early in the process
                adjustments_made = True

        # 4. Encourage optimism if too many negatives
        negative_count = sum(1 for insight in self.insights.values() if "negative" in str(insight).lower())
        if negative_count > len(self.insights) / 2:  # If more than half insights are negative
            if HatColor.YELLOW not in self.agenda:
                self.agenda.append(HatColor.YELLOW)  # Add positive thinking
                adjustments_made = True

        # 5. Add creative thinking if stuck
        if len(self.agenda) > 3 and HatColor.GREEN not in self.agenda[-3:]:  # If not in last 3 steps
            self.agenda.append(HatColor.GREEN)  # Add creative thinking towards the end
            adjustments_made = True

        # 6. Ensure comprehensive coverage
        all_hats = set(HatColor)
        used_hats = set(self.insights.keys()).union(set(self.agenda))
        missing_hats = all_hats - used_hats - {HatColor.BLUE}
        if missing_hats:
            self.agenda.extend(missing_hats)
            adjustments_made = True

        # 7. Limit repetitive thinking
        self.agenda = list(dict.fromkeys(self.agenda))  # Remove duplicates while preserving order

        # 8. Add final review if nearing conclusion
        if len(self.agenda) <= 2 and HatColor.BLUE not in self.agenda:
            self.agenda.append(HatColor.BLUE)  # Add a final review
            adjustments_made = True

        # 9. Randomize if stuck in a loop
        if not adjustments_made and len(self.insights) > 10:  # If no changes after many rounds
            random.shuffle(self.agenda)  # Randomize the remaining agenda to break potential loops

        print("Adjusted agenda:", [hat.value for hat in self.agenda])

    def start_process(self):
        self.start_time = time.time()
        print("Starting the decision-making process.")
        self.print_agenda()

    def switch_hat(self, new_hat: HatColor):
        self.current_hat = new_hat
        print(f"\nSwitching to {new_hat.value} Hat thinking.")
        return self._get_hat_context(new_hat)

    def _get_hat_context(self, hat: HatColor) -> Dict[str, Any]:
        context = {
            "shared_context": self.shared_context,
            "previous_insights": {k.value: v for k, v in self.insights.items() if k != hat},
        }
        return context

    def add_insight(self, hat: HatColor, insight: Any):
        self.insights[hat] = insight
        print(f"Added insight from {hat.value} Hat: {insight}")
        self._update_shared_context(hat, insight)
        self.adjust_agenda()  # Call adjust_agenda after each new insight

    def _update_shared_context(self, hat: HatColor, insight: Any):
        # Logic to update shared context based on new insights
        # This is a simplified version; you might want to make this more sophisticated
        if isinstance(insight, dict):
            self.shared_context.update(insight)
        else:
            self.shared_context[f"{hat.value}_insight"] = insight

    def summarize_progress(self):
        print("\nCurrent progress:")
        for hat, insight in self.insights.items():
            print(f"{hat.value} Hat: {insight}")
        print("\nShared Context:", self.shared_context)

    def check_time(self):
        elapsed_time = time.time() - self.start_time
        print(f"Time elapsed: {elapsed_time:.2f} seconds")

    def print_agenda(self):
        print("Current Agenda:", [hat.value for hat in self.agenda])

    def conclude_process(self):
        print("\nConcluding the decision-making process.")
        self.summarize_progress()
        print("Generating final synthesis...")
        # Here you would call your Response Synthesizer
        final_synthesis = self.synthesize_response()
        print("Final Synthesis:", final_synthesis)
        print("Decision process completed.")

    def synthesize_response(self) -> str:
        # This is a placeholder for the actual response synthesis logic
        synthesis = "Based on the insights gathered:\n"
        for hat, insight in self.insights.items():
            synthesis += f"- From {hat.value} Hat perspective: {insight}\n"
        synthesis += "\nRecommended course of action: [Your synthesized decision/recommendation here]"
        return synthesis

    def simulate_hat_agent(self, hat: HatColor, context: Dict[str, Any]) -> str:
        # This is a placeholder for actual hat agent logic
        # In a real implementation, this would call the specific LLM for each hat
        responses = {
            HatColor.WHITE: "Facts: Market share is 15%, competitor's share is 25%",
            HatColor.RED: "high_emotion: Team feels frustrated about market position",
            HatColor.BLACK: "major_obstacle: Limited budget for marketing",
            HatColor.YELLOW: "Opportunity: Emerging market in neighboring countries",
            HatColor.GREEN: "Idea: Partner with influencers for cost-effective marketing",
            HatColor.BLUE: "Process: We need more creative solutions, let's revisit Green hat",
        }
        return responses.get(hat, "No specific insight generated")

    def orchestrate_process(self, problem_statement: str, problem_type: str):
        self.start_process()
        self.shared_context["problem_statement"] = problem_statement
        self.set_initial_agenda(problem_type)

        max_iterations = 15  # Prevent infinite loops
        iteration = 0

        while self.agenda and iteration < max_iterations:
            hat = self.agenda.pop(0)
            context = self.switch_hat(hat)
            insight = self.simulate_hat_agent(hat, context)  # Replace with actual hat agent call
            self.add_insight(hat, insight)
            self.summarize_progress()
            self.check_time()
            self.print_agenda()
            iteration += 1

        self.conclude_process()


# Usage example
if __name__ == "__main__":
    orchestrator = BlueHatOrchestrator()
    orchestrator.orchestrate_process("How can we improve our product's market share?", "creative")
