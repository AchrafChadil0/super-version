# registry.py
from dataclasses import dataclass


@dataclass
class ToolConfig:
    name: str
    purpose: str  # One-line summary
    when_to_use: str  # Clear trigger conditions
    parameters: dict[str, str]  # param_name: description
    behavior_steps: list[str]
    response_format: dict | None = None  # Expected return structure
    validation_check: list[str]  | None = None
    confirmation_templates: list[str]  | None = None
    contextual_awareness: list[str]  | None = None
    critical_rules: list[str] | None = None
    examples: list[str] | None = None
    execution_notes: list[str] | None = None  # Timing, UI feedback, etc.

    def to_description(self) -> str:
        """Convert structured data to LLM-optimized description"""
        parts = [f"{self.purpose}\n", "WHEN TO USE:", self.when_to_use]

        # When to use (most important - comes first)

        # Parameters (essential for correct calls)
        if self.parameters:
            parts.append("\nREQUIRED PARAMETERS:")
            for param, desc in self.parameters.items():
                parts.append(f"- {param}: {desc}")

        # Execution notes (user experience)
        if self.execution_notes:
            parts.append("\nEXECUTION NOTES:")
            for note in self.execution_notes:
                parts.append(f"- {note}")

        # Behavior (what happens internally)
        if self.behavior_steps:
            parts.append("\nBEHAVIOR:")
            for i, step in enumerate(self.behavior_steps, 1):
                parts.append(f"{i}. {step}")

        # Response format (helps LLM parse results)
        if self.response_format:
            parts.append("\nRESPONSE FORMAT:")
            parts.append(self._format_response_structure(self.response_format))


        if self.validation_check:
            parts.append("\nVALIDATION CHECK:")
            for check in self.validation_check:
                parts.append(f"- {check}")

        if self.confirmation_templates:
            parts.append("\nCONFIRMATION TEMPLATES:")
            for template in self.confirmation_templates:
                parts.append(f"- {template}")

        if self.contextual_awareness:
            parts.append("\nCONTEXTUAL AWARENESS:")
            for awareness in self.contextual_awareness:
                parts.append(f"- {awareness}")

        # Critical rules (decision logic)
        if self.critical_rules:
            parts.append("\nCRITICAL RULES:")
            for rule in self.critical_rules:
                parts.append(f"- {rule}")

        # Examples (concrete patterns)
        if self.examples:
            parts.append("\nEXAMPLES:")
            for example in self.examples:
                parts.append(example)

        return "\n".join(parts)

    def _format_response_structure(self, structure: dict, indent: int = 0) -> str:
        """Format response structure as readable schema"""
        lines = []
        prefix = "  " * indent
        for key, value in structure.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_response_structure(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)


# Define tool configuration
