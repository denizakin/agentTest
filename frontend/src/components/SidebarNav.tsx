import { Stack, NavLink } from "@mantine/core";
import { IconActivity, IconChartLine, IconChartPie, IconHome2, IconListCheck, IconRocket, IconSettings } from "@tabler/icons-react";
import { useLocation, Link } from "react-router-dom";

const nav = [
  { label: "Coins", to: "/coins", icon: IconHome2 },
  { label: "Strategies", to: "/strategies", icon: IconChartLine },
  { label: "Backtests", to: "/backtests", icon: IconRocket },
  { label: "Optimizations", to: "/optimizations", icon: IconSettings },
  { label: "WF Analysis", to: "/wf", icon: IconChartPie },
  { label: "Activity", to: "/activity", icon: IconActivity },
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
