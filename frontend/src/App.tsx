import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { HomePage } from "./pages/HomePage";
import { DetectPage } from "./pages/DetectPage";
import { MaladiesPage } from "./pages/MaladiesPage";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="detecter" element={<DetectPage />} />
        <Route path="maladies" element={<MaladiesPage />} />
      </Route>
    </Routes>
  );
}

export default App;
