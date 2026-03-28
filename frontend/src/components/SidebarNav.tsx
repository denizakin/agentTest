import { Stack, NavLink } from "@mantine/core";
import { IconActivity, IconChartLine, IconChartPie, IconHome2, IconKey, IconRocket, IconSettings, IconTrendingUp } from "@tabler/icons-react";
import { useLocation, Link } from "react-router-dom";

const nav = [
  { label: "Coins", to: "/coins", icon: IconHome2 },
  { label: "Strategies", to: "/strategies", icon: IconChartLine },
  { label: "Backtests", to: "/backtests", icon: IconRocket },
  { label: "Optimizations", to: "/optimizations", icon: IconSettings },
  { label: "WF Analysis", to: "/wf", icon: IconChartPie },
  { label: "Trades", to: "/trades", icon: IconTrendingUp },
  { label: "Activity", to: "/activity", icon: IconActivity },
  { label: "Accounts", to: "/accounts", icon: IconKey },
];

export default function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  return (
    <Stack gap="xs">
      {nav.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.to;
        return (
          <NavLink
            key={item.to}
            component={Link}
            to={item.to}
            label={item.label}
            leftSection={<Icon size={16} />}
            active={active}
            variant={active ? "filled" : "light"}
            onClick={onNavigate}
          />
        );
      })}
    </Stack>
  );
}
