import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, Group, Select, Stack, Text, Textarea, TextInput, Box } from "@mantine/core";
import { useForm } from "react-hook-form";
import { z } from "zod";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { linter, Diagnostic } from "@codemirror/lint";
import { useState } from "react";

const schema = z.object({
  name: z.string().min(2, "Name required"),
  status: z.enum(["draft", "prod", "archived"]),
  tag: z.string().optional(),
  notes: z.string().optional(),
  code: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  onSubmit?: (values: FormValues) => void | Promise<void>;
  defaultValues?: Partial<FormValues>;
  submitting?: boolean;
  submitLabel?: string;
};

export default function StrategyForm({ onSubmit, defaultValues, submitting = false, submitLabel = "Save" }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      status: "draft",
      ...defaultValues,
    },
  });

  const submit = (values: FormValues) => {
    return onSubmit?.(values);
  };

  const status = watch("status");
  const code = watch("code");
  const [codeHeight, setCodeHeight] = useState(600);

  // Simple Python linter for basic syntax checks
  const pythonLinter = linter((view) => {
    const diagnostics: Diagnostic[] = [];
    const code = view.state.doc.toString();
    const lines = code.split('\n');

    // Check for basic Python syntax issues
    let bracketStack: { char: string; line: number; col: number }[] = [];
    const bracketPairs: Record<string, string> = { '(': ')', '[': ']', '{': '}' };
    const closingBrackets: Record<string, string> = { ')': '(', ']': '[', '}': '{' };

    lines.forEach((line, lineIdx) => {
      // Check for bracket matching
      for (let col = 0; col < line.length; col++) {
        const char = line[col];

        if (char in bracketPairs) {
          bracketStack.push({ char, line: lineIdx, col });
        } else if (char in closingBrackets) {
          const expected = closingBrackets[char];
          const last = bracketStack.pop();

          if (!last || last.char !== expected) {
            const pos = view.state.doc.line(lineIdx + 1).from + col;
            diagnostics.push({
              from: pos,
              to: pos + 1,
              severity: 'error',
              message: last
                ? `Mismatched bracket: expected '${bracketPairs[last.char]}' but found '${char}'`
                : `Unexpected closing bracket '${char}'`
            });
          }
        }
      }

      // Check for common Python mistakes
      if (line.trim().endsWith(':') && lineIdx < lines.length - 1) {
        const nextLine = lines[lineIdx + 1];
        if (nextLine.trim() && !nextLine.startsWith(' ') && !nextLine.startsWith('\t')) {
          const pos = view.state.doc.line(lineIdx + 2).from;
          diagnostics.push({
            from: pos,
            to: pos + nextLine.length,
            severity: 'warning',
            message: 'Expected indented block'
          });
        }
      }

      // Check for class inheritance from bt.Strategy
      const classMatch = line.match(/class\s+\w+\s*\(/);
      if (classMatch && !line.includes('bt.Strategy')) {
        const pos = view.state.doc.line(lineIdx + 1).from;
        diagnostics.push({
          from: pos,
          to: pos + line.length,
          severity: 'warning',
          message: 'Strategy class should inherit from bt.Strategy'
        });
      }
    });

    // Check for unclosed brackets
    if (bracketStack.length > 0) {
      bracketStack.forEach(({ char, line, col }) => {
        const pos = view.state.doc.line(line + 1).from + col;
        diagnostics.push({
          from: pos,
          to: pos + 1,
          severity: 'error',
          message: `Unclosed bracket '${char}' - expected '${bracketPairs[char]}'`
        });
      });
    }

    return diagnostics;
  });

  return (
    <Card withBorder radius="md" className="panel">
      <form onSubmit={handleSubmit(submit)}>
        <div style={{ display: "grid", gridTemplateColumns: "400px 1fr", gap: "24px" }}>
          {/* Left column: Form fields */}
          <Stack gap="sm">
            <Text fw={600}>Strategy Details</Text>
            <TextInput label="Name" placeholder="Mean reversion v1" {...register("name")} error={errors.name?.message} />
            <Select
              label="Status"
              data={[
                { value: "draft", label: "Draft" },
                { value: "prod", label: "Prod" },
                { value: "archived", label: "Archived" },
              ]}
              value={status}
              onChange={(val) => setValue("status", (val as FormValues["status"]) || "draft")}
            />
            <TextInput label="Tag" placeholder="e.g. momentum, mean-reversion" {...register("tag")} />
            <Textarea label="Notes" minRows={3} {...register("notes")} />

            <Group justify="flex-end" mt="md">
              <Button type="submit" loading={submitting}>
                {submitLabel}
              </Button>
            </Group>
          </Stack>

          {/* Right column: Code editor */}
          <Stack gap="xs">
            <Group justify="space-between">
              <Text fw={600}>Code (Python) - Must inherit from bt.Strategy</Text>
              <Group gap="xs">
                <Button size="xs" variant="subtle" onClick={() => setCodeHeight(h => Math.min(h + 100, 1200))}>
                  + Height
                </Button>
                <Button size="xs" variant="subtle" onClick={() => setCodeHeight(h => Math.max(h - 100, 300))}>
                  - Height
                </Button>
              </Group>
            </Group>
            <Box
              style={{
                border: "1px solid var(--mantine-color-gray-4)",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <CodeMirror
                value={code || ""}
                height={`${codeHeight}px`}
                extensions={[python(), pythonLinter]}
                onChange={(value) => setValue("code", value)}
                placeholder={`# Enter your strategy code here
# Example:
import backtrader as bt

class MyStrategy(bt.Strategy):
    params = dict(period=20)

    def __init__(self):
        self.sma = bt.indicators.SMA(period=self.p.period)

    def next(self):
        if not self.position and self.data.close[0] > self.sma[0]:
            self.buy()
        elif self.position and self.data.close[0] < self.sma[0]:
            self.close()`}
                basicSetup={{
                  lineNumbers: true,
                  highlightActiveLineGutter: true,
                  highlightSpecialChars: true,
                  foldGutter: true,
                  drawSelection: true,
                  dropCursor: true,
                  allowMultipleSelections: true,
                  indentOnInput: true,
                  bracketMatching: true,
                  closeBrackets: true,
                  autocompletion: true,
                  rectangularSelection: true,
                  crosshairCursor: true,
                  highlightActiveLine: true,
                  highlightSelectionMatches: true,
                  closeBracketsKeymap: true,
                  searchKeymap: true,
                  foldKeymap: true,
                  completionKeymap: true,
                  lintKeymap: true,
                }}
              />
            </Box>
          </Stack>
        </div>
      </form>
    </Card>
  );
}
