# Prompt Guide - Perplexity

URL Source: https://docs.perplexity.ai/guides/prompt-guide

Markdown Content:
Prompt Guide - Perplexity

===============

[Perplexity home page![Image 1: light logo](https://mintlify.s3.us-west-1.amazonaws.com/perplexity/logo/SonarByPerplexity.svg)![Image 2: dark logo](https://mintlify.s3.us-west-1.amazonaws.com/perplexity/logo/Sonar_Wordmark_Light.svg)](https://labs.perplexity.ai/)

Search docs

Ctrl K

*   [Playground](https://labs.perplexity.ai/)
*   [Playground](https://labs.perplexity.ai/)

Search...

Navigation

Guides

Prompt Guide

[Home](https://docs.perplexity.ai/home)[Models](https://docs.perplexity.ai/models/model-cards)[Guides](https://docs.perplexity.ai/guides/getting-started)[API Reference](https://docs.perplexity.ai/api-reference/chat-completions)[Changelog](https://docs.perplexity.ai/changelog/changelog)[System Status](https://docs.perplexity.ai/system-status/system-status)[FAQ](https://docs.perplexity.ai/faq/faq)[Roadmap](https://docs.perplexity.ai/feature-roadmap)[Discussions](https://docs.perplexity.ai/discussions/discussions)

##### Guides

*   [Initial Setup](https://docs.perplexity.ai/guides/getting-started)
*   [API Group](https://docs.perplexity.ai/guides/api-organization)
*   [Pricing](https://docs.perplexity.ai/guides/pricing)
*   [Rate Limits and Usage Tiers](https://docs.perplexity.ai/guides/usage-tiers)
*   [Prompt Guide](https://docs.perplexity.ai/guides/prompt-guide)
*   [Search Domain Filter Guide](https://docs.perplexity.ai/guides/search-domain-filters)
*   [Structured Outputs Guide](https://docs.perplexity.ai/guides/structured-outputs)
*   [Image Guide](https://docs.perplexity.ai/guides/image-guide)
*   [Date Range Filter Guide](https://docs.perplexity.ai/guides/date-range-filter-guide)
*   [User Location Filter Guide](https://docs.perplexity.ai/guides/user-location-filter-guide)
*   [Search Context Size](https://docs.perplexity.ai/guides/search-context-size-guide)
*   [Sonar Cookbook](https://docs.perplexity.ai/guides/cookbook)
*   [Perplexity Crawlers](https://docs.perplexity.ai/guides/bots)
*   [Integrating MCP with Perplexity's Sonar API](https://docs.perplexity.ai/guides/mcp-server)

Guides

Prompt Guide
============

[​](https://docs.perplexity.ai/guides/prompt-guide#system-prompt)

System Prompt
--------------------------------------------------------------------------------

You can use the system prompt to provide instructions related to style, tone, and language of the response.

The real-time search component of our models does not attend to the system prompt.

**Example of a system prompt**

Copy

```
You are a helpful AI assistant.

Rules:
1. Provide only the final answer. It is important that you do not include any explanation on the steps below.
2. Do not show the intermediate steps information.

Steps:
1. Decide if the answer should be a brief sentence or a list of suggestions.
2. If it is a list of suggestions, first, write a brief and natural introduction based on the original query.
3. Followed by a list of suggestions, each suggestion should be split by two newlines.
```

[​](https://docs.perplexity.ai/guides/prompt-guide#user-prompt)

User Prompt
----------------------------------------------------------------------------

You should use the user prompt to pass in the actual query for which you need an answer for. The user prompt will be used to kick off a real-time web search to make sure the answer has the latest and the most relevant information needed.

**Example of a user prompt**

Copy

```
What are the best sushi restaurants in the world currently?
```

[​](https://docs.perplexity.ai/guides/prompt-guide#web-search-models%3A-general-prompting-guidelines)

Web Search Models: General Prompting Guidelines
======================================================================================================================================================

Our web search-powered models combine the capabilities of LLMs with real-time web searches. Understanding how they differ from traditional LLMs will help you craft more effective prompts.

[​](https://docs.perplexity.ai/guides/prompt-guide#best-practices-for-prompting-web-search-models)

Best Practices for Prompting Web Search Models
--------------------------------------------------------------------------------------------------------------------------------------------------

Be Specific and Contextual
--------------------------

Unlike traditional LLMs, our web search models require specificity to retrieve relevant search results. Adding just 2-3 extra words of context can dramatically improve performance.

**Good Example**: "Explain recent advances in climate prediction models for urban planning"

**Poor Example**: "Tell me about climate models"

Avoid Few-Shot Prompting
------------------------

While few-shot prompting works well for traditional LLMs, it confuses web search models by triggering searches for your examples rather than your actual query.

**Good Example**: "Summarize the current research on mRNA vaccine technology"

**Poor Example**: "Here's an example of a good summary about vaccines: [example text]. Now summarize the current research on mRNA vaccines."

Think Like a Web Search User
----------------------------

Craft prompts with search-friendly terms that would appear on relevant web pages. Consider how experts in the field would describe the topic online.

**Good Example**: "Compare the energy efficiency ratings of heat pumps vs. traditional HVAC systems for residential use"

**Poor Example**: "Tell me which home heating is better"

Provide Relevant Context
------------------------

Include critical context to guide the web search toward the most relevant content, but keep prompts concise and focused.

**Good Example**: "Explain the impact of the 2023 EU digital markets regulations on app store competition for small developers"

**Poor Example**: "What are the rules for app stores?"

[​](https://docs.perplexity.ai/guides/prompt-guide#web-search-model-pitfalls-to-avoid)

Web Search Model Pitfalls to Avoid
--------------------------------------------------------------------------------------------------------------------------

Overly Generic Questions
------------------------

Generic prompts lead to scattered web search results and unfocused responses. Always narrow your scope.

**Avoid**: "What's happening in AI?"

**Instead**: "What are the three most significant commercial applications of generative AI in healthcare in the past year?"

Traditional LLM Techniques
--------------------------

Prompting strategies designed for traditional LLMs often don't work well with web search models. Adapt your approach accordingly.

**Avoid**: "Act as an expert chef and give me a recipe for sourdough bread. Start by explaining the history of sourdough, then list ingredients, then…"

**Instead**: "What's a reliable sourdough bread recipe for beginners? Include ingredients and step-by-step instructions."

Complex Multi-Part Requests
---------------------------

Complex prompts with multiple unrelated questions can confuse the search component. Focus on one topic per query.

**Avoid**: "Explain quantum computing, and also tell me about regenerative agriculture, and provide stock market predictions."

**Instead**: "Explain quantum computing principles that might impact cryptography in the next decade."

Assuming Search Intent
----------------------

Don't assume the model will search for what you intended without specific direction. Be explicit about exactly what information you need.

**Avoid**: "Tell me about the latest developments."

**Instead**: "What are the latest developments in offshore wind energy technology announced in the past 6 months?"

### [​](https://docs.perplexity.ai/guides/prompt-guide#advanced-techniques)

Advanced Techniques

We recommend for users _not_ to tune language parameters such as `temperature`, as the default settings for these have already been optimized.

Parameter Optimization
----------------------

Adjust model parameters based on your specific needs:

*   **Search Domain Filter**: Limit results to trusted sources for research-heavy queries.
*   **Search Context Size**: Use "high" for comprehensive research questions and "low" for simple factual queries.

Example configuration for technical documentation:

Copy

```json
{
  "search_domain_filter": ["wikipedia.org", "docs.python.org"],
  "web_search_options": {
    "search_context_size": "medium"
  }
}
```

### [​](https://docs.perplexity.ai/guides/prompt-guide#tips-for-different-query-types)

Tips for Different Query Types

| Query Type | Best Practices |
| --- | --- |
| **Factual Research** | • Use specific questions • Use search domain filters for academic sources • Consider "high" search context size |
| **Creative Content** | • Provide detailed style guidelines in system prompt • Specify tone, voice, and audience |
| **Technical Questions** | • Include relevant technical context • Specify preferred programming language/framework • Use domain filters for documentation sites |
| **Analysis & Insights** | • Request step-by-step reasoning • Ask for specific metrics or criteria |

[Rate Limits and Usage Tiers](https://docs.perplexity.ai/guides/usage-tiers)[Search Domain Filter Guide](https://docs.perplexity.ai/guides/search-domain-filters)

[twitter](https://x.com/PPLXDevs)[linkedin](https://www.linkedin.com/company/perplexity-ai/)[discord](https://discord.com/invite/perplexity-ai)[github](https://github.com/ppl-ai/api-discussion)[website](https://labs.perplexity.ai/)
