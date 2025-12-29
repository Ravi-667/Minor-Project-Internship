import json
import os
import asyncio
import re
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from mem0 import Memory
from memory import add_message, get_recent_history
from dotenv import load_dotenv
load_dotenv()

# --- NEW IMPORT ---
try:
    from linkup import LinkupClient
except ImportError:
    LinkupClient = None
    print("⚠️ Warning: 'linkup-sdk' not found. Research mode will be disabled.")

# --- CONFIGURATION ---
QDRANT_URL = "http://localhost:6333" 
EMBED_MODEL = "nomic-embed-text:v1.5"
LLM_MODEL = "deepseek-r1:7b"
LINKUP_API_KEY = os.getenv("LINKUP_API_KEY")  # <--- PASTE KEY HERE or use os.getenv("LINKUP_API_KEY")

class WebAgent:
    def __init__(self):
        print("\n[INIT] 🚀 Starting WebAgent...")
        
        # ... (Existing Model Init) ...
        self.router = ChatOllama(model=LLM_MODEL, format="json", temperature=0)
        self.tutor = ChatOllama(model=LLM_MODEL, temperature=0.3)
        self.coder = ChatOllama(model="qwen2.5-coder", temperature=0.2)
        self.vision = ChatOllama(model="llava:7b", temperature=0.1)

        # ... (Existing DB Init) ...
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.vector_store = QdrantVectorStore(
            client=QdrantClient(url=QDRANT_URL),
            collection_name="study_knowledge_base",
            embedding=self.embeddings,
        )
        
        # ... (Existing Mem0 Init) ...
        mem0_config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {"url": QDRANT_URL, "collection_name": "user_long_term_memory"}
            },
            "embedder": {"provider": "ollama", "config": {"model": EMBED_MODEL}},
            "llm": {"provider": "ollama", "config": {"model": LLM_MODEL, "temperature": 0}}
        }
        self.user_memory = Memory.from_config(mem0_config)
        self.user_id = "local_user"

        # --- INIT LINKUP CLIENT ---
        if LinkupClient and LINKUP_API_KEY:
            self.linkup = LinkupClient(api_key=LINKUP_API_KEY)
            print("[INIT] 🌐 Linkup API Connected (Research Mode Ready)")
        else:
            self.linkup = None

        # --- STATE ---
        self.mode = "chat"
        self.quiz_data = {"topic": None, "question": None, "score": 0, "count": 0}
        self.study_data = {"syllabus": [], "index": 0}
        
        print("[INIT] ✅ System Ready!\n")

    # --- HELPER: SAVE FILE (Existing) ---
    def _save_file_to_disk(self, filename, content):
        workspace_dir = "workspace"
        if not os.path.exists(workspace_dir): os.makedirs(workspace_dir)
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(workspace_dir, safe_filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f: f.write(content)
            return f"✅ **File Saved:** `{file_path}`"
        except Exception as e: return f"❌ **Error:** {str(e)}"

    async def get_response(self, user_query, image_data=None):
        print(f"\n[INPUT] 📥 User said: '{user_query}'")
        add_message("user", user_query)
        chat_history = get_recent_history(limit=20)
        clean_query = re.sub(r'<think>.*?</think>', '', user_query, flags=re.DOTALL)

        # 0. EXIT COMMANDS
        if clean_query.lower() in ["stop", "exit", "quit", "end"]:
            self.mode = "chat"
            yield "🛑 **Mode Deactivated.** Returning to normal chat."
            return

        # 1. VISION MODE
        if image_data:
            yield "👁️ **Vision Mode**\n\n"
            full_resp = "👁️ **Vision Mode**\n\n"
            async for chunk in self._run_vision(user_query, image_data): 
                full_resp += chunk
                yield chunk
            add_message("assistant", full_resp)
            return

        # 2. ACTIVE MODE HANDLING (Quiz/Study)
        if self.mode == "quiz":
            full_resp = ""
            async for chunk in self._handle_quiz_loop(clean_query):
                full_resp += chunk
                yield chunk
            add_message("assistant", full_resp)
            return 
        elif self.mode == "study":
            full_resp = ""
            async for chunk in self._handle_study_loop(clean_query):
                full_resp += chunk
                yield chunk
            add_message("assistant", full_resp)
            return

        # 3. ROUTING (The Brain)
        lower_q = clean_query.lower()
        
        if "quiz" in lower_q or "test me" in lower_q:
            tool = "quiz_start"
        elif "syllabus" in lower_q or "teach me" in lower_q:
            tool = "study_start"
        # RAG Triggers (Local Files)
        elif any(k in lower_q for k in ["doc", "file", "pdf", "context", "notes", "written", "summary", "lecture"]):
            tool = "rag"
        # CODER Triggers
        elif "code" in lower_q or "python" in lower_q or "function" in lower_q or "save" in lower_q:
            tool = "coder"
        # RESEARCH Triggers (Internet)
        elif any(k in lower_q for k in ["search", "internet", "online", "google", "find out", "latest", "news", "linkup"]):
            tool = "research"
        else:
            tool = await self._route_query(clean_query, chat_history)
        
        print(f"[ROUTER] 🔀 Decision: {tool.upper()}")

        # 4. EXECUTE TOOL
        if tool == "quiz_start":
            topic = clean_query.lower().replace("quiz on", "").replace("quiz about", "").replace("quiz", "").strip()
            if not topic: topic = "General Knowledge"
            
            # Save topic to state
            self.quiz_data["topic"] = topic
            self.mode = "quiz"
            # Remove this line: yield f"🎯 **Quiz Mode Started!**\n\n" 
            # (The loop handles the intro message now)
            
            async for chunk in self._handle_quiz_loop("start"): yield chunk
            return

        elif tool == "study_start":
            self.mode = "study"
            full_response = "📅 **Guided Study Mode Started!**\n\n"
            yield full_response
            async for chunk in self._init_study_mode(clean_query):
                full_response += chunk
                yield chunk

        elif tool == "coder":
            header = "🛠️ **Coding Mode**\n\n"
            yield header
            full_response = header 
            facts = "" 
            async for chunk in self._run_coder(clean_query, chat_history, facts):
                full_response += chunk
                yield chunk
        
        elif tool == "rag":
            header = "📚 **Searching Docs...**\n\n"
            yield header
            full_response = header
            facts = ""
            async for chunk in self._run_rag(clean_query, chat_history, facts):
                full_response += chunk
                yield chunk

        # --- NEW: RESEARCH MODE ---
        elif tool == "research":
            header = "🌐 **Researching Online...**\n\n"
            yield header
            full_response = header
            async for chunk in self._run_research(clean_query, chat_history):
                full_response += chunk
                yield chunk
        
        else:
            header = "🎓 **Tutor Mode**\n\n"
            yield header
            full_response = header
            facts = ""
            async for chunk in self._run_tutor(clean_query, chat_history, facts):
                full_response += chunk
                yield chunk

        # 5. FINALIZE
        add_message("assistant", full_response)
        if self.mode == "chat":
            asyncio.create_task(self._save_to_mem0_bg(clean_query, full_response))
        print("[DONE] ✅ Response finished.")

    # --- NEW: RESEARCH FUNCTION ---
    async def _run_research(self, query, history):
        if not self.linkup:
            yield "❌ **Error:** Linkup API Key is missing. Please add it to `agent.py`."
            return

        print(f"[RESEARCH] 🌍 Searching Linkup for: {query}")
        try:
            # 1. Perform Search (Depth='standard' is faster, 'deep' is thorough)
            # sourcedAnswer gives a synthesized answer + citations.
            # searchResults gives raw data chunks (Better for Agent context).
            response = self.linkup.search(
                query=query,
                depth="standard",
                output_type="searchResults" 
            )
            
            # 2. Format Results for LLM
            search_context = ""
            if response.results:
                for res in response.results:
                    search_context += f"Source: {res.name} ({res.url})\nContent: {res.content}\n\n"
            else:
                search_context = "No relevant online results found."

            # 3. Prompt the LLM
            prompt = f"""
            You are a Research Assistant with access to the internet.
            
            User Query: {query}
            
            Real-Time Search Results (Linkup API):
            {search_context}
            
            Chat History:
            {history}
            
            Task:
            Answer the user's question using the Search Results above. 
            Cite your sources if possible (e.g., [Source Name]).
            If the search results don't answer the question, admit it.
            """
            
            async for c in self.tutor.astream(prompt): 
                yield c.content
                
        except Exception as e:
            yield f"⚠️ **Research Error:** {str(e)}"
    async def _save_to_mem0_bg(self, query, response):
        try:
            self.user_memory.add(query, user_id=self.user_id, prompt=response)
            print("[BACKGROUND] ✨ Mem0 updated successfully.")
        except Exception as e:
            print(f"[ERROR] Mem0 Background Error: {e}")

    async def _route_query(self, query, history):
        print("[ROUTER] 🤔 Analyzing intent...")
        prompt = ChatPromptTemplate.from_template(
            """Analyze the query. History: {history}. Query: {query}
            RULES:
            - If user explicitly asks for a "quiz", "test me" -> "quiz_start".
            - If user asks to "teach me", "syllabus" -> "study_start".
            - If "pdf", "file", "notes", "search docs" -> "rag".
            - If "code", "python", "debug" -> "coder".
            - Otherwise -> "tutor".
            Return ONLY JSON: {{ "tool": "coder" | "rag" | "tutor" | "quiz_start" | "study_start" }}
            """
        )
        try:
            resp = self.router.invoke({"query": query, "history": history})
            content = resp.content
            # Strict JSON extraction
            json_str = content[content.find("{"):content.rfind("}")+1]
            return json.loads(json_str).get("tool", "tutor")
        except:
            print("[ROUTER] ⚠️ JSON parse failed, defaulting to Tutor")
            return "tutor"

    async def _handle_quiz_loop(self, user_input):
        # 1. START NEW QUIZ
        if user_input.lower() == "start" or self.quiz_data["question"] is None:
            print("[QUIZ] 🎲 Generating first question...")
            # Reset Score
            self.quiz_data["count"] = 0
            self.quiz_data["score"] = 0
            
            q_text = await self._generate_rag_question(self.quiz_data["topic"])
            self.quiz_data["question"] = q_text
            
            yield f"🎯 **Quiz Started: {self.quiz_data['topic']}**\n\n"
            yield f"**Question 1:**\n{q_text}\n\n"
            return

        # 2. GRADE ANSWER
        # 2. GRADE ANSWER (Replace this block)
        print("[QUIZ] 📝 Grading answer...")
        
        # STRONG PROMPT: Force a single word decision first
        grading_prompt = f"""
        You are a strict Grader.
        Question: {self.quiz_data['question']}
        Student Answer: {user_input}
        
        Rules:
        1. Determine if the answer is CORRECT or INCORRECT.
        2. Output format MUST be exactly:
           VERDICT: [CORRECT/INCORRECT]
           EXPLANATION: [Reasoning]
        """
        
        # Buffer the response so we can parse it
        grade_response = ""
        async for chunk in self.tutor.astream(grading_prompt):
            grade_response += chunk.content
        
        # 3. PARSE DECISION
        # We only count it if the AI explicitly wrote "VERDICT: CORRECT"
        final_verdict = "INCORRECT" 
        if "VERDICT: CORRECT" in grade_response:
            final_verdict = "CORRECT"
            self.quiz_data["score"] += 1
            
        self.quiz_data["count"] += 1
        
        # 4. SEND FEEDBACK TO USER
        # Clean up the "VERDICT:" tag so the user sees a nice message
        display_text = grade_response.replace("VERDICT:", "**Verdict:**").replace("EXPLANATION:", "\n**Explanation:**")
        yield f"{display_text}\n\n"
        
        # 5. SHOW SCORE & NEXT QUESTION
        yield f"📊 **Score: {self.quiz_data['score']} / {self.quiz_data['count']}**\n"
        yield "---\n**Next Question:**\n"
        
        q_text = await self._generate_rag_question(self.quiz_data["topic"])
        self.quiz_data["question"] = q_text
        yield q_text

    async def _generate_rag_question(self, topic):
        # Retry loop to ensure valid question generation
        for attempt in range(3):
            print(f"[QUIZ] 🎲 Generating question (Attempt {attempt+1}/3)...")
            
            # 1. Context Search
            results = await self.vector_store.asimilarity_search(str(topic), k=2)
            context = "\n".join([d.page_content for d in results]) if results else "General Knowledge"
            
            # 2. Strict Prompt
            prompt = f"""
            You are a strict Quiz Generator.
            Context: {context}
            Task: Create exactly ONE multiple-choice question about: {topic}.
            
            CRITICAL OUTPUT RULES:
            1. Output ONLY the question and 4 options (A, B, C, D).
            2. Do NOT write "Answer:", "Explanation:", or any conversational text.
            3. Do NOT explain why the other options are wrong.
            4. Stop immediately after Option D.
            
            Format:
            Question: [Text]
            A) [Option]
            B) [Option]
            C) [Option]
            D) [Option]
            """
            
            try:
                # 3. Generate
                response = await self.tutor.ainvoke(prompt)
                raw_content = response.content

                # 4. AGGRESSIVE CLEANING
                # Step A: Remove <think> tags (DeepSeek specific)
                clean_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
                
                # Step B: Hard Cut after Option D
                # We look for "D)" and the next newline
                if "D)" in clean_content:
                    # Find where "D)" starts
                    d_index = clean_content.rfind("D)")
                    # Find the end of that line (next newline)
                    end_of_d = clean_content.find("\n", d_index)
                    
                    if end_of_d != -1:
                        # Keep only up to the end of line D
                        clean_content = clean_content[:end_of_d].strip()
                    else:
                        # If D) is the last thing, keep it all
                        pass
                
                # Step C: Fallback cleanup for "Answer:" if "D)" wasn't found perfectly
                final_q = clean_content.split("Answer:")[0].split("Explanation:")[0].split("Correct Option:")[0].strip()

                # 5. Validation
                if len(final_q) > 20 and "A)" in final_q and "D)" in final_q:
                    return final_q
            
            except Exception as e:
                print(f"[QUIZ] Error: {e}")
                continue
        
        return "⚠️ **Error:** Could not generate a clean question. Type 'next' to retry."
    async def _run_rag(self, query, history, facts):
        print("[RAG] 📚 Querying Qdrant...")
        results = await self.vector_store.asimilarity_search(query, k=4)
        
        if not results: 
            print("[RAG] ❌ No docs found. Falling back to Tutor.")
            yield "⚠️ **No documents found.** Switching to general knowledge...\n\n"
            # Fallback to normal Tutor
            async for chunk in self._run_tutor(query, history, facts):
                yield chunk
            return
        
        print(f"[RAG] ✅ Found {len(results)} chunks.")
        context = "\n".join([f"📄 {os.path.basename(r.metadata.get('source','?'))}:\n{r.page_content}" for r in results])
        
        prompt = f"""You are a helpful assistant. Use the history and context to answer.
        
        History:
        {history}
        
        Facts (Long Term Memory):
        {facts}
        
        Context (Documents):
        {context}
        
        User Question:
        {query}
        """
        async for c in self.tutor.astream(prompt): 
            yield c.content

    def _save_file_to_disk(self, filename, content):
        """Tool: Writes code to the workspace directory."""
        workspace_dir = "workspace"
        if not os.path.exists(workspace_dir):
            os.makedirs(workspace_dir)
            
        # Security: Prevent path traversal (e.g., ../../system32)
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(workspace_dir, safe_filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ **File Saved:** `{file_path}`"
        except Exception as e:
            return f"❌ **Error Saving File:** {str(e)}"

    async def _run_coder(self, query, history, facts):
        print("[CODER] 💻 Analyzing request...")
        
        # 1. System Prompt with TOOL Instructions
        system_prompt = f"""
        You are an expert Python Coder with FILE ACCESS.
        
        History: {history}
        User Request: {query}
        
        RULES:
        1. If the user asks to SAVE code to a file, you MUST output a SINGLE JSON block.
        2. Format:
           ```json
           {{
             "action": "save_file",
             "filename": "example.py",
             "content": "print('Hello World')"
           }}
           ```
        3. If the user just asks a question, reply with normal text/code blocks.
        4. Do NOT include any text outside the JSON block if you are saving a file.
        """
        
        # 2. Invoke the model (Non-streaming first to check for JSON)
        response = await self.coder.ainvoke(system_prompt)
        content = response.content
        
        # 3. Check for Tool Use (JSON)
        # We look for the specific pattern of a JSON block
        if "```json" in content and "save_file" in content:
            try:
                # Extract JSON
                json_str = content.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_str)
                
                if data.get("action") == "save_file":
                    print(f"[AGENT] 🛠️  Tool Triggered: Writing {data['filename']}...")
                    result_msg = self._save_file_to_disk(data['filename'], data['content'])
                    
                    # Stream the result back to the user
                    yield result_msg
                    
                    # Optional: Provide a download link logic here if you want
                    yield f"\n\n*You can find this file in the `workspace/` folder.*"
                    return
            except Exception as e:
                print(f"[AGENT] ⚠️ JSON Parse Error: {e}")
                # Fallback: Just show the raw content if parsing fails
                yield content
        
        # 4. Standard Response (No file save requested)
        # If no JSON was detected, just stream the content normally
        yield content

    async def _run_tutor(self, query, history, facts):
        print("[TUTOR] 🎓 Generating explanation...")
        
        # FIX: Added 'History: {history}'
        prompt = f"""You are a helpful tutor.
        
        Chat History:
        {history}
        
        Facts about User:
        {facts}
        
        User Question:
        {query}
        """
        async for c in self.tutor.astream(prompt): 
            yield c.content
    async def _run_vision(self, query, b64_image):
        print("[VISION] 👁️ Analyzing image...")
        
        # FIX: "image_url" must be a dictionary with a "url" key
        msg = HumanMessage(content=[
            {"type": "text", "text": query},
            {
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
            }
        ])
        
        try:
            async for c in self.vision.astream([msg]): 
                yield c.content
        except Exception as e:
            print(f"[ERROR] Vision failed: {e}")
            yield f"❌ **Vision Error:** {str(e)}\n\n*Make sure you have run: `ollama pull llava:7b`*"

    # =========================================================================
    #  🎓 STUDY MODE LOGIC (Syllabus & Interactive Teaching)
    # =========================================================================

    async def _init_study_mode(self, query):
        """
        1. Extracts the topic from the user's query.
        2. Generates a structured syllabus using the LLM.
        3. Initializes the study state.
        """
        # Clean the topic string
        remove_words = ["teach", "me", "about", "syllabus", "for", "generate", "create", "a"]
        topic = query.lower()
        for word in remove_words:
            topic = topic.replace(word, "")
        topic = topic.strip().title()
        
        if not topic: 
            topic = "General Knowledge"

        yield f"📘 **Designing Course Structure for: {topic}...**\n\n"

        # Prompt for Syllabus Generation
        prompt = f"""
        You are an expert curriculum designer. Create a concise 4-step study syllabus for: {topic}.
        
        RULES:
        1. Return ONLY a valid JSON list of strings.
        2. No conversational filler (no "Here is the list").
        3. Example format: ["Introduction to {topic}", "Core Concepts", "Advanced Techniques", "Real-world Applications"]
        """
        
        try:
            # Generate and Parse
            response = await self.tutor.ainvoke(prompt)
            # Regex to find the list [...] inside the response
            match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if match:
                syllabus = json.loads(match.group(0))
            else:
                raise ValueError("No JSON found")
        except Exception as e:
            # Fallback if LLM fails JSON generation
            print(f"⚠️ Syllabus Error: {e}")
            syllabus = [f"Basics of {topic}", f"{topic} Core Concepts", f"Advanced {topic}", "Summary & Review"]

        # SAVE STATE
        self.study_data = {
            "topic": topic,
            "syllabus": syllabus,
            "index": 0,
            "active": True
        }

        # Display Plan to User
        yield f"**👨‍🏫 Here is your personalized study plan:**\n\n"
        for i, item in enumerate(syllabus):
            yield f"**{i+1}.** {item}\n"
        
        yield "\n👉 **Type 'Start' or 'Next' to begin the first lesson.**"

    async def _handle_study_loop(self, user_input):
        """
        Handles the interaction loop:
        - If user says 'next/start': Teaches the current module.
        - If user asks a question: Answers contextually based on the current lesson.
        """
        # Load State
        data = self.study_data
        syllabus = data["syllabus"]
        idx = data["index"]
        topic = data["topic"]

        # --- NAVIGATION LOGIC (User wants to move forward) ---
        nav_keywords = ["start", "next", "continue", "go", "yes", "ready"]
        if any(k in user_input.lower() for k in nav_keywords) and len(user_input.split()) < 5:
            
            # Check if course is finished
            if idx >= len(syllabus):
                yield "🎓 **Course Complete!**\n\nYou have finished all modules in this syllabus.\nType 'reset' to start a new topic or ask any other question."
                self.mode = "chat" # Exit mode
                self.study_data = {} # Clear data
                return

            # Get Current Module
            current_module = syllabus[idx]
            yield f"### 📖 Module {idx+1}: {current_module}\n\n"

            # Generate Lesson Content
            lesson_prompt = f"""
            You are a teacher explaining '{current_module}' as part of a course on '{topic}'.
            
            INSTRUCTIONS:
            - Explain the concept clearly and concisely.
            - Provide ONE simple code example or analogy if applicable.
            - Keep it engaging but brief (under 200 words).
            - Do not say "Module X". Just teach.
            """
            
            # Stream the Lesson
            async for chunk in self.tutor.astream(lesson_prompt):
                yield chunk.content
            
            # Advance Index
            self.study_data["index"] += 1
            yield "\n\n---\n*Type 'Next' to continue to the next module, or ask me a question about this lesson.*"

        # --- Q&A LOGIC (User has a question about the current lesson) ---
        else:
            # Contextual Answer
            current_context = syllabus[idx-1] if idx > 0 else "Introduction"
            
            yield "👨‍🏫 **Tutor:**\n"
            qna_prompt = f"""
            The student is taking a course on '{topic}'. 
            We just finished discussing '{current_context}'.
            
            Student Question: "{user_input}"
            
            Answer the question helpfully, keeping the context of the course in mind.
            """
            
            async for chunk in self.tutor.astream(qna_prompt):
                yield chunk.content
            
            yield "\n\n*(Type 'Next' when you are ready to move on)*"