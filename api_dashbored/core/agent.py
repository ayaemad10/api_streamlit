"""
ai_agent/agent.py
-----------------
Main AI Agent orchestrator.
Combines: context retrieval (RAG) + Ollama LLM + threat analysis.
"""

import sqlite3
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("ai_agent.agent")


SYSTEM_PROMPT = """You are SpectrumAI, an expert RF spectrum security analyst.
You help operators analyze RF anomalies including jamming attacks and unauthorized drone signals.
You have access to real-time detection data, historical patterns, and RF security knowledge.
Be concise, technical, and actionable. Always provide threat severity and recommended actions."""


class SpectrumAgent:
    """
    Orchestrates LLM + database context to answer spectrum security questions.
    Falls back to rule-based responses if Ollama is unavailable.
    """

    def __init__(self):
        self.ollama_url = self._get_ollama_url()

    def _get_ollama_url(self) -> str:
        try:
            from api.config import get_settings
            return get_settings().OLLAMA_BASE_URL
        except Exception:
            return "http://localhost:11434"

    async def chat(self, message: str, session_id: str = "default") -> dict:
        """
        Process a user message and return an AI response.

        Args:
            message:    User's question or command.
            session_id: Conversation session identifier.

        Returns:
            { answer: str, sources: list, model: str }
        """
        context = self._get_db_context()
        history = self._get_chat_history(session_id, limit=5)

        enriched_prompt = self._build_prompt(message, context, history)

        # Try Ollama first
        answer = await self._call_ollama(enriched_prompt)

        if answer is None:
            # Fallback: rule-based response
            answer = self._rule_based_response(message, context)
            model_used = "rule-based-fallback"
        else:
            model_used = "ollama/mistral"

        return {
            "answer": answer,
            "sources": ["spectrum.db", "rf_knowledge_base"],
            "model": model_used,
            "timestamp": datetime.now().isoformat(),
        }

    def _get_db_context(self) -> str:
        """Pull recent signals and stats from DB for context."""
        try:
            conn = sqlite3.connect("spectrum.db")
            cur = conn.cursor()

            cur.execute("""
                SELECT label, COUNT(*) as count, AVG(confidence) as avg_conf
                FROM signals GROUP BY label
            """)
            stats = cur.fetchall()

            cur.execute("""
                SELECT label, confidence, timestamp
                FROM signals ORDER BY timestamp DESC LIMIT 5
            """)
            recent = cur.fetchall()

            cur.execute("SELECT COUNT(*) FROM alerts")
            alert_count = cur.fetchone()[0]

            conn.close()

            lines = ["=== CURRENT SYSTEM STATUS ==="]
            lines.append(f"Total alerts triggered: {alert_count}")
            lines.append("Signal distribution:")
            for label, count, avg_conf in stats:
                lines.append(f"  {label}: {count} signals, avg confidence {avg_conf:.2%}")
            lines.append("Recent detections:")
            for label, conf, ts in recent:
                lines.append(f"  [{ts[:16]}] {label} ({conf:.2%})")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"DB context fetch failed: {e}")
            return "No database context available."

    def _get_chat_history(self, session_id: str, limit: int = 5) -> list:
        """Retrieve recent chat history for this session."""
        try:
            conn = sqlite3.connect("spectrum.db")
            cur = conn.cursor()
            cur.execute("""
                SELECT user_query, agent_response FROM chat_history
                WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?
            """, (session_id, limit))
            rows = cur.fetchall()
            conn.close()
            return list(reversed(rows))
        except Exception:
            return []

    def _build_prompt(self, message: str, context: str, history: list) -> str:
        """Compose the full prompt with system context and chat history."""
        parts = [SYSTEM_PROMPT, "\n", context, "\n"]

        if history:
            parts.append("=== CONVERSATION HISTORY ===")
            for user_q, agent_a in history:
                parts.append(f"User: {user_q}")
                parts.append(f"Assistant: {agent_a[:200]}...")

        parts.append(f"\nUser: {message}\nAssistant:")
        return "\n".join(parts)

    async def _call_ollama(self, prompt: str) -> str | None:
        """Call Ollama API. Returns None if unavailable."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": "mistral", "prompt": prompt, "stream": False},
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
                logger.warning(f"Ollama returned {resp.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Ollama unavailable: {e}")
            return None

    def _rule_based_response(self, message: str, context: str) -> str:
        """
        Fallback rule-based answers when Ollama is offline.
        Handles common spectrum security questions.
        """
        msg_lower = message.lower()

        if any(kw in msg_lower for kw in ["jamming", "jam"]):
            return (
                "**Jamming Attack Detected Protocol:**\n"
                "1. Verify signal continuity on backup frequencies\n"
                "2. Increase receiver gain and apply notch filters\n"
                "3. Switch to frequency-hopping spread spectrum if available\n"
                "4. Log event with timestamp and frequency for forensics\n"
                "5. Alert command: potential intentional interference\n\n"
                f"Current system status:\n{context}"
            )
        elif any(kw in msg_lower for kw in ["drone", "uav", "uas"]):
            return (
                "**Unauthorized Drone Signal Response:**\n"
                "1. Capture signal metadata (frequency, timing, pattern)\n"
                "2. Cross-reference with approved UAV frequencies\n"
                "3. Activate geo-fence verification\n"
                "4. Notify security personnel and initiate tracking\n"
                "5. Document for regulatory reporting\n\n"
                f"Current system status:\n{context}"
            )
        elif any(kw in msg_lower for kw in ["status", "summary", "report"]):
            return f"**System Status Summary:**\n\n{context}"
        elif any(kw in msg_lower for kw in ["normal", "safe"]):
            return "All monitored frequencies are within normal parameters. No anomalies detected in recent scans."
        else:
            return (
                f"I'm analyzing your query about: *{message}*\n\n"
                f"Based on current data:\n{context}\n\n"
                "For detailed analysis, ensure Ollama is running: `ollama serve` and model pulled: `ollama pull mistral`"
            )
