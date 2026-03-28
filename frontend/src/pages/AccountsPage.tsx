import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
  PasswordInput,
} from "@mantine/core";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import type { Account, CreateAccountRequest, UpdateAccountRequest } from "../api/types";

const PLATFORM_OPTIONS = [
  { value: "binance", label: "Binance" },
  { value: "okx", label: "OKX" },
];

const PLATFORM_COLORS: Record<string, string> = {
  binance: "yellow",
  okx: "blue",
};

type FormState = {
  name: string;
  platform: string;
  description: string;
  is_demo: boolean;
  api_key: string;
  secret_key: string;
};

const emptyForm: FormState = {
  name: "",
  platform: "binance",
  description: "",
  is_demo: false,
  api_key: "",
  secret_key: "",
};

export default function AccountsPage() {
  const qc = useQueryClient();
  const [modalOpened, setModalOpened] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [deleteTarget, setDeleteTarget] = useState<Account | null>(null);

  const accountsQuery = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: async () => {
      const res = await fetch("/api/accounts");
      if (!res.ok) throw new Error("Failed to fetch accounts");
      return res.json();
    },
  });

  const createMutation = useMutation({
    mutationFn: async (payload: CreateAccountRequest) => {
      const res = await fetch("/api/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Failed to create account");
      }
      return res.json();
    },
    onSuccess: () => {
      notifications.show({ title: "Account created", message: "Saved successfully", color: "green" });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      closeModal();
    },
    onError: (err: Error) => {
      notifications.show({ title: "Failed to create", message: err.message, color: "red" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateAccountRequest }) => {
      const res = await fetch(`/api/accounts/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Failed to update account");
      }
      return res.json();
    },
    onSuccess: () => {
      notifications.show({ title: "Account updated", message: "Updated successfully", color: "green" });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      closeModal();
    },
    onError: (err: Error) => {
      notifications.show({ title: "Failed to update", message: err.message, color: "red" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/accounts/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete account");
    },
    onSuccess: () => {
      notifications.show({ title: "Account deleted", message: "Deleted successfully", color: "green" });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      setDeleteTarget(null);
    },
    onError: (err: Error) => {
      notifications.show({ title: "Failed to delete", message: err.message, color: "red" });
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpened(true);
  };

  const openEdit = (account: Account) => {
    setEditing(account);
    setForm({
      name: account.name,
      platform: account.platform,
      description: account.description ?? "",
      is_demo: account.is_demo,
      api_key: account.api_key ?? "",
      secret_key: account.secret_key ?? "",
    });
    setModalOpened(true);
  };

  const closeModal = () => {
    setModalOpened(false);
    setEditing(null);
    setForm(emptyForm);
  };

  const handleSubmit = () => {
    if (!form.name.trim()) {
      notifications.show({ title: "Validation", message: "Name is required", color: "orange" });
      return;
    }
    const payload = {
      name: form.name.trim(),
      platform: form.platform as "binance" | "okx",
      description: form.description.trim() || undefined,
      is_demo: form.is_demo,
      api_key: form.api_key.trim() || undefined,
      secret_key: form.secret_key.trim() || undefined,
    };
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const accounts = accountsQuery.data ?? [];
  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Accounts</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={openCreate}>
          New Account
        </Button>
      </Group>

      {accountsQuery.isLoading && <Text c="dimmed">Loading...</Text>}
      {accountsQuery.isError && <Text c="red">Failed to load accounts</Text>}

      {accounts.length === 0 && !accountsQuery.isLoading && (
        <Text c="dimmed" style={{ textAlign: "center", padding: "40px" }}>
          No accounts yet. Click "New Account" to add one.
        </Text>
      )}

      {accounts.length > 0 && (
        <Table striped highlightOnHover style={{ fontSize: "13px" }}>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Platform</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Description</Table.Th>
              <Table.Th>API Key</Table.Th>
              <Table.Th>Created</Table.Th>
              <Table.Th style={{ width: 80 }}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {accounts.map((account) => (
              <Table.Tr key={account.id}>
                <Table.Td>{account.id}</Table.Td>
                <Table.Td>
                  <Text fw={500}>{account.name}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={PLATFORM_COLORS[account.platform] ?? "gray"} variant="light">
                    {account.platform.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Badge color={account.is_demo ? "violet" : "teal"} variant="light">
                    {account.is_demo ? "Demo" : "Real"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" lineClamp={1} style={{ maxWidth: 260 }}>
                    {account.description ?? "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" style={{ fontFamily: "monospace" }}>
                    {account.api_key ? `${account.api_key.slice(0, 8)}••••` : "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {new Date(account.created_at).toLocaleDateString("tr-TR")}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    <ActionIcon variant="subtle" onClick={() => openEdit(account)} title="Edit">
                      <IconEdit size={15} />
                    </ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      onClick={() => setDeleteTarget(account)}
                      title="Delete"
                    >
                      <IconTrash size={15} />
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* Create / Edit Modal */}
      <Modal
        opened={modalOpened}
        onClose={closeModal}
        title={editing ? "Edit Account" : "New Account"}
        size="md"
      >
        <Stack gap="sm">
          <TextInput
            label="Name"
            placeholder="My Binance Account"
            required
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <Select
            label="Platform"
            data={PLATFORM_OPTIONS}
            value={form.platform}
            onChange={(v) => setForm((f) => ({ ...f, platform: v ?? "binance" }))}
            required
          />
          <Switch
            label="Demo Account"
            description="Enable for paper trading / testnet accounts"
            checked={form.is_demo}
            onChange={(e) => setForm((f) => ({ ...f, is_demo: e.currentTarget.checked }))}
          />
          <Textarea
            label="Description"
            placeholder="Optional notes about this account"
            rows={2}
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
          <TextInput
            label="API Key"
            placeholder="Enter API key"
            value={form.api_key}
            onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
          />
          <PasswordInput
            label="Secret Key"
            placeholder="Enter secret key"
            value={form.secret_key}
            onChange={(e) => setForm((f) => ({ ...f, secret_key: e.target.value }))}
          />
          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={closeModal}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} loading={isPending}>
              {editing ? "Save Changes" : "Create"}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal
        opened={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Account"
        size="sm"
      >
        <Stack gap="sm">
          <Text size="sm">
            Are you sure you want to delete <Text span fw={700}>{deleteTarget?.name}</Text>?
            This action cannot be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              color="red"
              loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
