import { BrowserRouter, Routes, Route } from "react-router-dom";
import LessonPage from "./pages/LessonPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/lesson/:lessonId" element={<LessonPage />} />
        <Route
          path="*"
          element={
            <div style={{ padding: "2rem", textAlign: "center" }}>
              <h2>Trang không tồn tại</h2>
              <p>Vui lòng kiểm tra lại đường dẫn.</p>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
