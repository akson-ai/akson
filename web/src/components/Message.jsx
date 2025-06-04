import { useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { FaTrash, FaCopy, FaChevronRight, FaChevronDown } from "react-icons/fa6";
import { FaTools } from "react-icons/fa";

function Message({ id, role, name, content, toolCall, toolCallId, category, onDelete }) {
  const [isHovered, setIsHovered] = useState(false);
  const [isToolExpanded, setIsToolExpanded] = useState(false);
  const categoryTag = category ? `chat-bubble-${category}` : "";

  const renderMarkdownContent = (content) => (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const code = String(children).replace(/\n$/, "");
          return match ? (
            <div className="relative group">
              <button
                className="absolute top-2 right-2 btn btn-xs btn-ghost btn-square opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => navigator.clipboard.writeText(code)}
                title="Copy code"
              >
                <FaCopy />
              </button>
              <SyntaxHighlighter style={vscDarkPlus} language={match[1]} {...props}>
                {code}
              </SyntaxHighlighter>
            </div>
          ) : (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
      }}
    >
      {content}
    </Markdown>
  );
  return (
    <div
      className={`chat ${role === "user" ? "chat-end" : "chat-start"}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="chat-image avatar">
        <div className="w-10 rounded-full bg-base-300 place-content-center">
          <div className="text-2xl place-self-center">{role === "user" ? "👤" : "🤖"}</div>
        </div>
      </div>
      <div className="chat-header">
        <time className="text-xs opacity-50">{name || "You"}</time>
      </div>
      <div className={`chat-bubble ${categoryTag} mt-1`}>
        {!(content || toolCall || toolCallId) ? (
          <div className="flex items-center">
            <div className="loading loading-spinner loading-sm mr-2"></div>
            <span>Thinking...</span>
          </div>
        ) : (
          <div>
            {role === "tool" ? (
              <div>
                <button
                  className="flex items-center gap-2 text-sm opacity-70 hover:opacity-100 transition-opacity cursor-pointer w-full text-left"
                  onClick={() => setIsToolExpanded(!isToolExpanded)}
                >
                  {isToolExpanded ? <FaChevronDown /> : <FaChevronRight />}
                  <FaTools />
                  <span>Tool Result</span>
                </button>
                {isToolExpanded && (
                  <div className="mt-2 border-t border-base-300 pt-2">
                    <div className={categoryTag ? "" : "prose"}>{renderMarkdownContent(content)}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className={categoryTag ? "" : "prose"}>{renderMarkdownContent(content)}</div>
            )}
            {toolCall && (
              <div className="mt-2 border-t border-base-300 pt-2">
                <div className="flex items-center gap-2 text-sm opacity-70">
                  <FaTools />
                  <span>Tool Call</span>
                </div>
                <div className="mt-1 space-y-1">
                  <div className="text-sm font-mono bg-base-200 p-2 rounded">
                    <span className="text-primary">{toolCall.name}</span>
                    &nbsp;
                    <span className="text-secondary">{toolCall.arguments}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      {(content || toolCall) && (
        <div className={`chat-footer mt-1 ${isHovered ? "visible" : "invisible"}`}>
          <>
            <button
              className="btn btn-xs btn-ghost btn-square"
              onClick={() => navigator.clipboard.writeText(content)}
              title="Copy message"
            >
              <FaCopy />
            </button>
            <button
              className="btn btn-xs btn-ghost btn-square btn-error"
              onClick={() => onDelete(id)}
              title="Delete message"
            >
              <FaTrash />
            </button>
          </>
        </div>
      )}
    </div>
  );
}

export default Message;
