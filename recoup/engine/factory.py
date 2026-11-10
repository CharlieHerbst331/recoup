"""Engine composition exports; design/02 §4.5."""

from recoup.contracts.capabilities import scan_capabilities
from recoup.contracts.interfaces import EngineParts
from recoup.engine.gates import ProposalValidator
from recoup.engine.harness import HarnessEngine
from recoup.engine.ingest import Ingestor
from recoup.engine.llm import FakeLLM, ReplayLLM
from recoup.engine.tools import ToolSessionFactory


def build_engine(config) -> EngineParts:
    tools = ToolSessionFactory()
    caps = scan_capabilities(llm_mode=config.llm, vision=getattr(config, "vision", False))
    vision_llm = get_llm(config) if caps["vision"] and caps["pillow"] else None
    return EngineParts(
        engine=HarnessEngine(tools),
        ingestor=Ingestor(vision_llm=vision_llm),
        validator=ProposalValidator(),
        tools=tools,
    )


def get_llm(config):
    if config.llm == "fake":
        return FakeLLM()
    if config.llm == "replay":
        return ReplayLLM(config.model)
    if config.llm == "live":
        from recoup.engine.llm.openai_compat import OpenAICompatLLM

        return OpenAICompatLLM(config.model, base_url=config.base_url)
    raise ValueError(f"Unknown LLM mode: {config.llm}")


class HarnessController:
    name = "harness"

    def __init__(self, parts, llm):
        self.parts, self.llm = parts, llm

    def react(self, world, events, run_id):
        self.parts.engine.handle(world, self.llm, run_id)
        if not events:
            for view in world.list_cases():
                self.parts.engine.investigate(world, view.case_id, self.llm, run_id)


def harness_controller(parts, llm):
    return HarnessController(parts, llm)
