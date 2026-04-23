import "../styles/lesson.css";

export default function LoadingSpinner() {
  return (
    <div className="loading-container">
      <div className="spinner" role="status" aria-label="Đang tải..."></div>
      <p className="loading-text">Đang tải bài học...</p>
    </div>
  );
}
