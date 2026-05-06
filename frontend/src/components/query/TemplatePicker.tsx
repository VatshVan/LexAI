interface TemplatePickerProps {
  templates: any[];
  selectedTemplate: string | null;
  onSelect: (template: string | null) => void;
}

export function TemplatePicker({
  templates,
  selectedTemplate,
  onSelect
}: TemplatePickerProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {templates.map((template) => (
        <button
          key={template.template_name}
          onClick={() =>
            onSelect(
              selectedTemplate === template.template_name ? null : template.template_name
            )
          }
          className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
            selectedTemplate === template.template_name
              ? "border-accent bg-accent/10 text-accent"
              : "border-surface-600 text-gray-400 hover:border-accent/50"
          }`}
        >
          {template.display_name}
        </button>
      ))}
    </div>
  );
}
