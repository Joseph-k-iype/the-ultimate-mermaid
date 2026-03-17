import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import MermaidRenderer from "./MermaidRenderer";

interface Props {
  content: string;
}

export default function MarkdownRenderer({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            if (className === "language-mermaid") {
              return (
                <MermaidRenderer code={String(children).trim()} />
              );
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
