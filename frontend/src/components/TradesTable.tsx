import { Table, Text } from "@mantine/core";

type Trade = {
  id: string;
  side: "buy" | "sell";
  price: number;
  qty: number;
  ts: string;
};

export default function TradesTable({ trades }: { trades: Trade[] }) {
  if (!trades.length) {
    return <Text c="dimmed">No trades yet.</Text>;
  }

  return (
    <Table striped highlightOnHover withRowBorders={false} verticalSpacing="xs">
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Side</Table.Th>
          <Table.Th>Price</Table.Th>
          <Table.Th>Qty</Table.Th>
          <Table.Th>Time</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {trades.map((t) => (
          <Table.Tr key={t.id}>
            <Table.Td>{t.side.toUpperCase()}</Table.Td>
            <Table.Td>{t.price}</Table.Td>
            <Table.Td>{t.qty}</Table.Td>
            <Table.Td>{t.ts}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
