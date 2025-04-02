import os

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=os.environ["OPENAI_API_VERSION"],
    temperature=0,
)


@tool
def content_writer(text: str, input_type: str, output_type: str) -> str:
    """Transforms text for various purposes."""
    system_prompt = """
        You are content writer.
        User will give you a text and you will rewrite it.

        Input type: {input_type}
        Output type: {output_type}
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", text),
        ],
    )
    chain = prompt | llm
    response = chain.invoke({"input_type": input_type, "output_type": output_type})
    assert isinstance(response, AIMessage)
    assert isinstance(response.content, str)
    return response.content
