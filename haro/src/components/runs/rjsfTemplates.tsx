/**
 * Custom RJSF templates for Tailwind CSS.
 *
 * RJSF defaults to Bootstrap class names which don't render in Tailwind projects.
 * These templates replace the default rendering with Tailwind-compatible markup.
 */

import type {
  ArrayFieldTemplateProps,
  ArrayFieldItemTemplateProps,
  BaseInputTemplateProps,
  FieldTemplateProps,
  ObjectFieldTemplateProps,
} from "@rjsf/utils";

const inputClasses =
  "w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

export function FieldTemplate(props: FieldTemplateProps) {
  const { id, label, required, children, rawErrors, schema } = props;
  // Hide the root object wrapper label
  if (id === "root") return <>{children}</>;
  return (
    <div className="mb-3">
      {schema.type !== "object" && schema.type !== "array" && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          {label}
          {required && <span className="text-red-400 ml-0.5">*</span>}
        </label>
      )}
      {children}
      {rawErrors && rawErrors.length > 0 && (
        <p className="text-red-400 text-xs mt-1">{rawErrors.join(", ")}</p>
      )}
    </div>
  );
}

export function ObjectFieldTemplate(props: ObjectFieldTemplateProps) {
  return (
    <div className="space-y-1">
      {props.properties.map((prop) => prop.content)}
    </div>
  );
}

export function ArrayFieldTemplate(props: ArrayFieldTemplateProps) {
  const { title, items, canAdd, onAddClick, required, schema } = props;
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-slate-300 mb-1">
        {title}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {schema.description && (
        <p className="text-xs text-slate-400 mb-2">{schema.description}</p>
      )}
      <div className="space-y-2">{items}</div>
      {canAdd && (
        <button
          type="button"
          onClick={onAddClick}
          className="mt-2 text-sm text-blue-400 hover:text-blue-300"
          data-testid="rjsf-add-item"
        >
          + Add item
        </button>
      )}
    </div>
  );
}

export function ArrayFieldItemTemplate(props: ArrayFieldItemTemplateProps) {
  const { children, buttonsProps } = props;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1">{children}</div>
      {buttonsProps.hasRemove && (
        <button
          type="button"
          onClick={buttonsProps.onRemoveItem}
          className="text-red-400 hover:text-red-300 text-sm px-2 py-1"
          title="Remove"
        >
          ✕
        </button>
      )}
    </div>
  );
}

export function BaseInputTemplate(props: BaseInputTemplateProps) {
  const { id, type, value, onChange, onBlur, onFocus, required, readonly } =
    props;
  return (
    <input
      id={id}
      type={type || "text"}
      value={value ?? ""}
      required={required}
      readOnly={readonly}
      onChange={(e) =>
        onChange(e.target.value === "" ? undefined : e.target.value)
      }
      onBlur={(e) => onBlur(id, e.target.value)}
      onFocus={(e) => onFocus(id, e.target.value)}
      className={inputClasses}
    />
  );
}

export function SelectWidget(props: {
  id: string;
  value: unknown;
  options: { enumOptions?: { value: unknown; label: string }[] };
  onChange: (val: unknown) => void;
  required?: boolean;
}) {
  const { id, value, options, onChange, required } = props;
  return (
    <select
      id={id}
      value={String(value ?? "")}
      required={required}
      onChange={(e) => onChange(e.target.value)}
      className={inputClasses}
    >
      {options.enumOptions?.map((opt) => (
        <option key={String(opt.value)} value={String(opt.value)}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
