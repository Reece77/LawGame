import { BrowserRouter, Route, Routes } from 'react-router';
import { AutomationScreen } from './screens/AutomationScreen';
import { ClientScreen } from './screens/ClientScreen';
import { ClientsScreen } from './screens/ClientsScreen';
import { FamilyScreen } from './screens/FamilyScreen';
import { FinanceScreen } from './screens/FinanceScreen';
import { FounderScreen } from './screens/FounderScreen';
import { GameLayout } from './screens/GameLayout';
import { InboxScreen } from './screens/InboxScreen';
import { MainMenu } from './screens/MainMenu';
import { MarketScreen } from './screens/MarketScreen';
import { MatterScreen } from './screens/MatterScreen';
import { MattersScreen } from './screens/MattersScreen';
import { NewGameScreen } from './screens/NewGameScreen';
import { OrgScreen } from './screens/OrgScreen';
import { HistoryScreen } from './screens/HistoryScreen';
import { OverviewScreen } from './screens/OverviewScreen';
import { PartnershipScreen } from './screens/PartnershipScreen';
import { PeopleScreen } from './screens/PeopleScreen';
import { PersonScreen } from './screens/PersonScreen';
import { PracticesScreen } from './screens/PracticesScreen';
import { PressScreen } from './screens/PressScreen';
import { RankingsScreen } from './screens/RankingsScreen';
import { OfficesScreen } from './screens/OfficesScreen';
import { RecruitmentScreen } from './screens/RecruitmentScreen';
import { RivalScreen } from './screens/RivalScreen';
import { SavesScreen } from './screens/SavesScreen';
import { SettingsScreen } from './screens/SettingsScreen';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainMenu />} />
        <Route path="/new" element={<NewGameScreen />} />
        <Route path="/saves" element={<SavesScreen />} />
        <Route path="/settings" element={<SettingsScreen />} />
        <Route path="/game/:slug" element={<GameLayout />}>
          <Route index element={<OverviewScreen />} />
          <Route path="people" element={<PeopleScreen />} />
          <Route path="people/:personId" element={<PersonScreen />} />
          <Route path="recruitment" element={<RecruitmentScreen />} />
          <Route path="inbox" element={<InboxScreen />} />
          <Route path="org" element={<OrgScreen />} />
          <Route path="automation" element={<AutomationScreen />} />
          <Route path="matters" element={<MattersScreen />} />
          <Route path="matters/:matterId" element={<MatterScreen />} />
          <Route path="clients" element={<ClientsScreen />} />
          <Route path="clients/:clientId" element={<ClientScreen />} />
          <Route path="practices" element={<PracticesScreen />} />
          <Route path="finance" element={<FinanceScreen />} />
          <Route path="market" element={<MarketScreen />} />
          <Route path="market/rivals/:firmId" element={<RivalScreen />} />
          <Route path="rankings" element={<RankingsScreen />} />
          <Route path="offices" element={<OfficesScreen />} />
          <Route path="press" element={<PressScreen />} />
          <Route path="partnership" element={<PartnershipScreen />} />
          <Route path="history" element={<HistoryScreen />} />
          <Route path="founder" element={<FounderScreen />} />
          <Route path="family" element={<FamilyScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
