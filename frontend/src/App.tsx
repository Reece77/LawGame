import { BrowserRouter, Route, Routes } from 'react-router';
import { ClientScreen } from './screens/ClientScreen';
import { ClientsScreen } from './screens/ClientsScreen';
import { FinanceScreen } from './screens/FinanceScreen';
import { GameLayout } from './screens/GameLayout';
import { InboxScreen } from './screens/InboxScreen';
import { MainMenu } from './screens/MainMenu';
import { MatterScreen } from './screens/MatterScreen';
import { MattersScreen } from './screens/MattersScreen';
import { NewGameScreen } from './screens/NewGameScreen';
import { OrgScreen } from './screens/OrgScreen';
import { OverviewScreen } from './screens/OverviewScreen';
import { PeopleScreen } from './screens/PeopleScreen';
import { PersonScreen } from './screens/PersonScreen';
import { PracticesScreen } from './screens/PracticesScreen';
import { RecruitmentScreen } from './screens/RecruitmentScreen';
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
          <Route path="matters" element={<MattersScreen />} />
          <Route path="matters/:matterId" element={<MatterScreen />} />
          <Route path="clients" element={<ClientsScreen />} />
          <Route path="clients/:clientId" element={<ClientScreen />} />
          <Route path="practices" element={<PracticesScreen />} />
          <Route path="finance" element={<FinanceScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
