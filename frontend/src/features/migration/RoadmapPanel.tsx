import { ShieldCheck } from "lucide-react";

const roadmapItems = [
  "群聊、新闻、RAG 与学习记忆已接入可恢复的服务端流程。",
  "当前优先收口核心学习闭环、恢复语义与窄屏体验。",
  "产品前端统一为 React，旧 Streamlit 运行层已移除。"
];

export function RoadmapPanel() {
  return (
    <section className="panel compact" id="prd-roadmap">
      <div className="panel-header">
        <div>
          <h2>核心能力边界</h2>
          <span>围绕主学习闭环持续收口</span>
        </div>
        <ShieldCheck size={18} />
      </div>
      <ul className="roadmap-list">
        {roadmapItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
