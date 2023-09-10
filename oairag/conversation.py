from langchain import OpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.schema import Document

from .config import Settings

settings = Settings.get_settings()


async def __run_summarise_chain(
    docs: list[Document], llm: OpenAI = None, **kwargs
) -> str:
    if llm is None:
        chain = load_summarize_chain(
            llm=get_llm_model(), chain_type=kwargs.get("chain_type", "refine")
        )
    else:
        chain = load_summarize_chain(
            llm=llm, chain_type=kwargs.get("chain_type", "refine")
        )

    return await chain.arun(docs)


def get_llm_model(**kwargs):
    return OpenAI(
        openai_api_key=settings.openai_api_key,
        model_name=settings.openai_default_llm_model,
        **kwargs,
    )
