"""
Prompt templates for Simulink analysis.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    system_prompt: str
    user_template: str
    
    def format(
        self,
        model_summary: str,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> str:
        """Format the prompt with given variables."""
        user_content = self.user_template.format(
            model_summary=model_summary,
            query=query,
            context=context or "No additional context available."
        )
        
        return f"<|system|>\n{self.system_prompt}\n<|user|>\n{user_content}\n<|assistant|>\n"


# Default prompt templates
DEFAULT_SYSTEM_PROMPT = """You are SimulinkGPT, an expert MATLAB/Simulink assistant. 
Your role is to help users debug Simulink models, provide improvement suggestions, and give guidelines.

You have access to:
1. A parsed representation of the Simulink model structure
2. Relevant knowledge from Simulink documentation and best practices

When responding:
- Be specific about block names and paths from the model
- Provide actionable suggestions with clear explanations
- If you identify issues, explain why they are problems and how to fix them
- Use proper technical terminology
- Format your responses clearly with headers and bullet points
- If you're unsure about something, say so instead of guessing"""


DEBUGGING_TEMPLATE = """## Task: Debug Simulink Model

### Model Structure:
{model_summary}

### Knowledge Base Context:
{context}

### User Query:
{query}

Please analyze the model structure above and provide:
1. Any potential issues or errors you can identify
2. Specific blocks that might be causing problems
3. Suggested fixes for any issues found

Format your response with clear sections for each issue found."""


IMPROVEMENTS_TEMPLATE = """## Task: Suggest Improvements

### Model Structure:
{model_summary}

### Knowledge Base Context:
{context}

### User Query:
{query}

Please provide:
1. Suggestions for improving model performance
2. Recommendations for better modeling practices
3. Potential optimizations for simulation speed
4. Improvements for code generation (if applicable)

Be specific about which blocks or subsystems could be improved."""


GUIDELINES_TEMPLATE = """## Task: Provide Guidelines

### Model Structure:
{model_summary}

### Knowledge Base Context:
{context}

### User Query:
{query}

Please provide:
1. Relevant guidelines and best practices
2. Configuration recommendations
3. Design pattern suggestions
4. Any applicable standards or conventions

Reference specific Simulink features and blocks where relevant."""


GENERAL_TEMPLATE = """## Task: Simulink Analysis

### Model Structure:
{model_summary}

### Knowledge Base Context:
{context}

### User Query:
{query}

Please provide a helpful, detailed response addressing the user's query. Use the model structure and knowledge base to provide specific, actionable advice."""


# Pre-defined templates for different tasks
TEMPLATES: Dict[str, PromptTemplate] = {
    "debug": PromptTemplate(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        user_template=DEBUGGING_TEMPLATE
    ),
    "improve": PromptTemplate(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        user_template=IMPROVEMENTS_TEMPLATE
    ),
    "guidelines": PromptTemplate(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        user_template=GUIDELINES_TEMPLATE
    ),
    "general": PromptTemplate(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        user_template=GENERAL_TEMPLATE
    )
}


def get_template(task_type: str = "general") -> PromptTemplate:
    """Get a prompt template by task type."""
    return TEMPLATES.get(task_type, TEMPLATES["general"])


def detect_task_type(query: str) -> str:
    """Detect the task type from the query."""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["debug", "error", "issue", "problem", "wrong", "fail"]):
        return "debug"
    elif any(word in query_lower for word in ["improve", "optimize", "better", "enhance", "performance"]):
        return "improve"
    elif any(word in query_lower for word in ["guideline", "best practice", "how to", "recommend", "should"]):
        return "guidelines"
    else:
        return "general"
