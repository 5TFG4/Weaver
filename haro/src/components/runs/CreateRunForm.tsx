/**
 * CreateRunForm Component
 *
 * Modal form for creating a new trading run.
 * Uses RJSF to render dynamic config forms based on strategy JSON Schema.
 */

import { useState } from "react";
import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";
import { useStrategies } from "../../hooks/useStrategies";
import type { RunCreate, RunMode } from "../../api/types";
import {
  FieldTemplate,
  ObjectFieldTemplate,
  ArrayFieldTemplate,
  ArrayFieldItemTemplate,
  BaseInputTemplate,
  SelectWidget,
} from "./rjsfTemplates";

export interface CreateRunFormProps {
  onSubmit: (data: RunCreate) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function CreateRunForm({
  onSubmit,
  onCancel,
  isSubmitting = false,
}: CreateRunFormProps) {
  const { data: strategies } = useStrategies();
  const [strategyId, setStrategyId] = useState("");
  const [mode, setMode] = useState<RunMode>("backtest");
  const [configData, setConfigData] = useState<Record<string, unknown>>({});

  const selectedStrategy = strategies?.find((s) => s.id === strategyId);
  const configSchema = selectedStrategy?.config_schema;

  function handleSubmit() {
    const config = { ...configData };
    if (mode === "backtest") {
      if (
        typeof config.backtest_start === "string" &&
        !config.backtest_start.endsWith("Z")
      ) {
        config.backtest_start = config.backtest_start + ":00Z";
      }
      if (
        typeof config.backtest_end === "string" &&
        !config.backtest_end.endsWith("Z")
      ) {
        config.backtest_end = config.backtest_end + ":00Z";
      }
    }
    onSubmit({
      strategy_id: strategyId,
      mode,
      config,
    });
  }

  return (
    <div
      data-testid="create-run-form"
      className="bg-slate-800 rounded-lg border border-slate-700 p-6"
    >
      <h2 className="text-lg font-semibold text-white mb-4">Create New Run</h2>
      <div className="space-y-4">
        <div>
          <label
            htmlFor="strategy-id"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Strategy
          </label>
          <select
            id="strategy-id"
            aria-label="Strategy"
            value={strategyId}
            onChange={(e) => {
              setStrategyId(e.target.value);
              setConfigData({});
            }}
            required
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select strategy...</option>
            {strategies?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="run-mode"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Mode
          </label>
          <select
            id="run-mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as RunMode)}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="backtest">Backtest</option>
            <option value="paper">Paper</option>
            <option value="live">Live</option>
          </select>
        </div>

        {mode === "backtest" && (
          <>
            <div>
              <label
                htmlFor="backtest-start"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Start Time
              </label>
              <input
                id="backtest-start"
                type="datetime-local"
                onChange={(e) =>
                  setConfigData((prev) => ({
                    ...prev,
                    backtest_start: e.target.value,
                  }))
                }
                className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label
                htmlFor="backtest-end"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                End Time
              </label>
              <input
                id="backtest-end"
                type="datetime-local"
                onChange={(e) =>
                  setConfigData((prev) => ({
                    ...prev,
                    backtest_end: e.target.value,
                  }))
                }
                className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </>
        )}

        {configSchema && (
          <Form
            schema={configSchema as Record<string, unknown>}
            validator={validator}
            formData={configData}
            onChange={(e) => setConfigData(e.formData)}
            uiSchema={{ "ui:submitButtonOptions": { norender: true } }}
            templates={{
              FieldTemplate,
              ObjectFieldTemplate,
              ArrayFieldTemplate,
              ArrayFieldItemTemplate,
              BaseInputTemplate,
            }}
            widgets={{ SelectWidget }}
          >
            <></>
          </Form>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {isSubmitting ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
