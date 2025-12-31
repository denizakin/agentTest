import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, Group, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { useForm } from "react-hook-form";
import { z } from "zod";

const schema = z.object({
  name: z.string().min(2, "Name required"),
  status: z.enum(["draft", "prod", "archived"]),
  notes: z.string().optional(),
  code: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  onSubmit?: (values: FormValues) => void;
  defaultValues?: Partial<FormValues>;
};

export default function StrategyForm({ onSubmit, defaultValues }: Props) {
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
    onSubmit?.(values);
  };

  const status = watch("status");

  return (
    <Card withBorder radius="md" className="panel">
      <form onSubmit={handleSubmit(submit)}>
        <Stack gap="sm">
          <Text fw={600}>Create Strategy</Text>
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
          <Textarea label="Notes" minRows={3} {...register("notes")} />
          <Textarea label="Code (optional)" minRows={6} placeholder="# pseudo-code" {...register("code")} />
          <Group justify="flex-end">
            <Button type="submit">Save</Button>
          </Group>
        </Stack>
      </form>
    </Card>
  );
}
