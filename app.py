import json
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class StudyBuddy:
    def __init__(self, model_name="deepseek-r1:7b"):
        print(f"Initializing Study Buddy with {model_name}...")
        self.llm = ChatOllama(model=model_name, temperature=0.3)
        self.current_topic = "General Knowledge"

    # ==========================================
    # MODE 1: GUIDED LEARNING (Syllabus Based)
    # ==========================================
    def start_guided_learning(self):
        topic = input("\nWhat do you want to learn about? (e.g., Python, World War II): ")
        self.current_topic = topic
        
        print(f"\nGenerating syllabus for {topic}...")
        
        # Step 1: Generate a Syllabus using a specific Prompt
        syllabus_prompt = ChatPromptTemplate.from_template(
            """You are an expert teacher. Create a short 4-step study syllabus for the topic: {topic}.
            Return ONLY a JSON list of strings. Example: ["History", "Key Events", "Aftermath"]
            Do not add any conversational text.
            """
        )
        
        chain = syllabus_prompt | self.llm | StrOutputParser()
        response = chain.invoke({"topic": topic})
        
        try:
            # Clean up potential markdown code blocks (```json ... ```)
            cleaned_json = response.replace("```json", "").replace("```", "").strip()
            syllabus = json.loads(cleaned_json)
        except:
            # Fallback if model talks too much
            syllabus = [f"Basics of {topic}", f"Advanced {topic}", f"Summary"]

        print(f"\n--- Syllabus for {topic} ---")
        for i, item in enumerate(syllabus):
            print(f"{i+1}. {item}")
            
        # Step 2: Loop through the syllabus
        for step in syllabus:
            print(f"\n\n>>> Current Module: {step}")
            input("Press Enter to start this module...")
            
            # Explain the concept
            explain_prompt = ChatPromptTemplate.from_template(
                "You are a teacher. Explain the concept of '{subtopic}' regarding '{topic}' clearly and concisely."
            )
            chain = explain_prompt | self.llm | StrOutputParser()
            
            print("\nAI Teacher:")
            for chunk in chain.stream({"subtopic": step, "topic": topic}):
                print(chunk, end="", flush=True)
            
            print("\n")
            # Simple check before moving on
            if input("Type 'next' for next topic or 'quit' to exit: ").lower() == 'quit':
                return

    # ==========================================
    # MODE 2: QUIZ MODE (Interactive Loop)
    # ==========================================
    def start_quiz_mode(self):
        topic = input("\nWhat topic should I quiz you on? ")
        score = 0
        rounds = 3
        
        print(f"\nStarting a {rounds}-question quiz on {topic}!")
        
        for i in range(rounds):
            print(f"\n--- Question {i+1}/{rounds} ---")
            
            # Step 1: Generate Question
            q_prompt = ChatPromptTemplate.from_template(
                """You are a Quiz Master. Generate ONE medium-difficulty question about {topic}.
                Output format: Just the question text. Do not provide the answer yet.
                """
            )
            chain = q_prompt | self.llm | StrOutputParser()
            question = chain.invoke({"topic": topic})
            print(f"Q: {question}")
            
            # Step 2: Get User Answer
            user_answer = input("Your Answer: ")
            
            # Step 3: Grade the Answer
            grade_prompt = ChatPromptTemplate.from_template(
                """You are a strict Grader.
                Question: {question}
                User Answer: {user_answer}
                
                Task:
                1. Determine if the answer is correct (Yes/No).
                2. Provide a short explanation.
                
                Format:
                CORRECT: [Yes/No]
                EXPLANATION: [Reasoning]
                """
            )
            grader_chain = grade_prompt | self.llm | StrOutputParser()
            feedback = grader_chain.invoke({"question": question, "user_answer": user_answer})
            
            print(f"\n>> Feedback:\n{feedback}")
            
            if "CORRECT: Yes" in feedback or "CORRECT: YES" in feedback:
                score += 1
                
        print(f"\n\n=== Quiz Finished! Score: {score}/{rounds} ===")

    # ==========================================
    # MAIN MENU (The "Router")
    # ==========================================
    def main_menu(self):
        while True:
            print("\n=========================")
            print(" AI STUDY COMPANION ")
            print("=========================")
            print("1. Guided Learning Mode")
            print("2. Quiz Mode")
            print("3. Exit")
            
            choice = input("\nSelect a mode (1-3): ")
            
            if choice == "1":
                self.start_guided_learning()
            elif choice == "2":
                self.start_quiz_mode()
            elif choice == "3":
                print("Goodbye!")
                break
            else:
                print("Invalid choice, try again.")

if __name__ == "__main__":
    # Ensure you have run: ollama pull deepseek-r1:7b
    bot = StudyBuddy(model_name="deepseek-r1:7b")
    bot.main_menu()