"""
RAG (Retrieval-Augmented Generation) Service Module
Handles knowledge retrieval and LLM queries
"""

import subprocess
import os

class RAGService:
    """Knowledge-based RAG system for agricultural advice."""
    
    def __init__(self, knowledge_base: str, class_to_title: dict):
        self.knowledge_base = knowledge_base.strip()
        self.class_to_title = class_to_title
    
    def get_block_for_class(self, disease_class: str) -> str:
        """Retrieve knowledge block for disease class."""
        title = self.class_to_title.get(disease_class)
        if not title:
            return self.knowledge_base
        
        blocks = self.knowledge_base.split("\n\n")
        for block in blocks:
            first_line = block.splitlines()[0].rstrip(":").strip()
            if first_line.lower() == title.lower():
                return block
        
        return self.knowledge_base
    
    def query(self, user_question: str, disease_class: str, llm_func=None) -> str:
        """
        Query RAG system for disease-specific advice.
        
        Args:
            user_question: User's question about disease/treatment
            disease_class: CNN-predicted disease class
            llm_func: Function to call LLM (optional, for future use)
        
        Returns:
            Formatted advice string with knowledge about the disease
        """
        filtered_knowledge = self.get_block_for_class(disease_class)
        disease_title = self.class_to_title.get(disease_class, disease_class)
        
        # Parse the knowledge block into simple sections so we can answer
        # user questions without requiring a full LLM. Sections are lines
        # that start with a dash or headings like 'Symptoms:', 'Cause:', etc.
        lines = [l.rstrip() for l in filtered_knowledge.splitlines() if l.strip()]
        sections = {}
        current_key = 'summary'
        sections[current_key] = []
        # Skip the very first title line if it is the block title
        idx = 0
        if lines and lines[0].endswith(':'):
            idx = 1

        for ln in lines[idx:]:
            ln = ln.strip()
            # Heading line like 'Symptoms:'
            if ln.endswith(':') and not ln.startswith('-'):
                current_key = ln.rstrip(':').lower()
                sections.setdefault(current_key, [])
                continue

            # List item (may contain a subheading like '- Symptoms: detail')
            if ln.startswith('-'):
                content = ln.lstrip('-').strip()
                if ':' in content:
                    k, v = content.split(':', 1)
                    key = k.strip().lower()
                    sections.setdefault(key, []).append(v.strip())
                else:
                    sections.setdefault(current_key, []).append(content)
                continue

            # Inline key:value lines
            if ':' in ln:
                k, v = ln.split(':', 1)
                key = k.strip().lower()
                sections.setdefault(key, []).append(v.strip())
            else:
                sections.setdefault(current_key, []).append(ln)

        q = (user_question or '').lower()

        # Simple keyword routing to sections
        if any(k in q for k in ['symptom', 'what is', 'how to identify', 'looks like']):
            answers = sections.get('symptoms', sections.get('summary'))
            source = 'Symptoms'
        elif any(k in q for k in ['prevent', 'prevention', 'avoid']):
            answers = sections.get('prevention', sections.get('summary'))
            source = 'Prevention'
        elif any(k in q for k in ['treatment', 'treat', 'chemical', 'organic', 'control']):
            # prefer organic then chemical
            oc = sections.get('organic control') or sections.get('organic')
            cc = sections.get('chemical control') or sections.get('chemical')
            combined = []
            if oc:
                combined.append('Organic Control: ' + '; '.join(oc))
            if cc:
                combined.append('Chemical Control: ' + '; '.join(cc))
            answers = combined if combined else sections.get('summary')
            source = 'Treatment/Control'
        elif any(k in q for k in ['cause', 'pathogen', 'what causes']):
            answers = sections.get('cause', sections.get('summary'))
            source = 'Cause'
        else:
            # Default: give a concise summary (symptoms + controls + prevention)
            parts = []
            if sections.get('symptoms'):
                parts.append('Symptoms: ' + '; '.join(sections.get('symptoms')))
            if sections.get('organic control') or sections.get('chemical control'):
                oc = sections.get('organic control') or []
                cc = sections.get('chemical control') or []
                if oc:
                    parts.append('Organic Control: ' + '; '.join(oc))
                if cc:
                    parts.append('Chemical Control: ' + '; '.join(cc))
            if sections.get('prevention'):
                parts.append('Prevention: ' + '; '.join(sections.get('prevention')))
            answers = parts if parts else sections.get('summary')
            source = 'Summary'

        # Format the response nicely
        if isinstance(answers, list):
            body = '\n'.join([('- ' + a) for a in answers if a])
        else:
            body = str(answers)

        response = f"Disease: {disease_title}\n\n{source}:\n{body}"
        return response


class LLMService:
    """Flexible offline LLM interface."""
    
    def __init__(self):
        self.llm_type = self._detect_llm()
    
    def _detect_llm(self) -> str:
        """Auto-detect available LLM runtime."""
        # Check Ollama
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, timeout=2, check=True)
            return "ollama"
        except:
            pass
        
        # Check llama-cpp-python
        try:
            import llama_cpp
            return "llama_cpp"
        except ImportError:
            pass
        
        return "stub"
    
    def query(self, prompt: str, timeout: int = 30) -> str:
        """Query LLM with given prompt."""
        
        if self.llm_type == "ollama":
            return self._query_ollama(prompt, timeout)
        elif self.llm_type == "llama_cpp":
            return self._query_llama_cpp(prompt)
        else:
            return self._query_stub(prompt)
    
    def _query_ollama(self, prompt: str, timeout: int) -> str:
        """Query via Ollama CLI."""
        try:
            process = subprocess.Popen(
                ["ollama", "run", "llama3.2:1b"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            output, error = process.communicate(prompt, timeout=timeout)
            if output and output.strip():
                return output.strip()
            return "⚠️ Ollama returned no output."
        except subprocess.TimeoutExpired:
            return "⚠️ Ollama timeout."
        except Exception as e:
            return f"❌ Ollama error: {str(e)}"
    
    def _query_llama_cpp(self, prompt: str) -> str:
        """Query via llama-cpp-python."""
        try:
            from llama_cpp import Llama
            model_path = os.getenv("LLAMA_MODEL_PATH")
            if not model_path or not os.path.exists(model_path):
                return "⚠️ LLAMA_MODEL_PATH not set or file not found."
            
            llm = Llama(model_path=model_path, n_gpu_layers=-1)
            resp = llm.create(prompt=prompt, max_tokens=512, temperature=0.1)
            if resp and resp.get("choices"):
                return resp["choices"][0].get("text", "").strip()
            return "⚠️ llama-cpp-python returned empty response."
        except Exception as e:
            return f"❌ llama-cpp-python error: {str(e)}"
    
    def _query_stub(self, prompt: str) -> str:
        """Stub response for testing."""
        return f"[STUB LLM] Query: {prompt[:100]}...\nResponse: Install Ollama or llama-cpp-python for real LLM."
