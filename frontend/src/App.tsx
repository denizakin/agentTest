import { AppShell, Burger, Group, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Outlet, Route, Routes } from "react-router-dom";
import SidebarNav from "./components/SidebarNav";
import CoinsPage from "./pages/CoinsPage";
import StrategiesPage from "./pages/StrategiesPage";
import BacktestsPage from "./pages/BacktestsPage";
import OptimizationsPage from "./pages/OptimizationsPage";
import WfAnalysisPage from "./pages/WfAnalysisPage";
import ActivityPage from "./pages/ActivityPage";

function AppLayout() {
  const [opened, { toggle }] = useDisclosure(true);

  return (
    <AppShell
      padding="md"
      header={{
        height: 60,
      }}
      navbar={{
        width: 240,
        breakpoint: "sm",
        collapsed: { mobile: !opened },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={4}>Auto-Trading Platform</Title>
          </Group>
          <Text size="sm" c="dimmed">
            Mock data view
          </Text>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <SidebarNav onNavigate={() => opened && toggle()} />
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<CoinsPage />} />
        <Route path="/coins" element={<CoinsPage />} />
        <Route path="/strategies" element={<StrategiesPage />} />
        <Route path="/backtests" element={<BacktestsPage />} />
        <Route path="/optimizations" element={<OptimizationsPage />} />
        <Route path="/wf" element={<WfAnalysisPage />} />
        <Route path="/activity" element={<ActivityPage />} />
      </Route>
    </Routes>
  );
}
