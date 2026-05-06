import { useQuery } from "@tanstack/react-query";
import { Send } from "lucide-react";

import { api } from "../../lib/axios";
import { Button } from "../ui/Button";
import { TemplatePicker } from "./TemplatePicker";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onTemplateSelect: (template: string | null) => void;
  selectedTemplate: string | null;
  onSubmit: () => void;
  submitting: boolean;
}

export function QueryInput({
  value,
  onChange,
  onTemplateSelect,
  selectedTemplate,
  onSubmit,
  submitting
}: Props) {
  const { data: templates = [] } = useQuery({
    queryKey: ["templates"],
    queryFn: () => api.get("/templates/")
  });

  const showTemplates = value.toLowerCase().includes("draft");

  return (
    <div className="space-y-3">
      <div className="relative">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) onSubmit();
          }}
          placeholder="Ask anything about your case documents... (Ctrl/Cmd + Enter to submit)"
          rows={4}
          className="w-full bg-surface-800 border border-surface-600 rounded-xl px-4 py-3 pr-12 text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:border-accent transition-colors"
        />
        <Button
          onClick={onSubmit}
          loading={submitting}
          disabled={!value.trim()}
          className="absolute bottom-3 right-3 p-2"
          aria-label="Submit"
        >
          <Send size={16} />
        </Button>
      </div>

      {showTemplates && (
        <TemplatePicker
          templates={templates as any[]}
          selectedTemplate={selectedTemplate}
          onSelect={onTemplateSelect}
        />
      )}

      {selectedTemplate && <p className="text-xs text-accent">Template: {selectedTemplate}</p>}
    </div>
  );
}
