function StatCard({
  title,
  value,
  icon,
  color,
  trend,
  trendText
}) {

  return (

    <div className="stat-card">

      <div className="stat-header">

        <div
          className="stat-icon"
          style={{
            backgroundColor: `${color}20`,
            color: color
          }}
        >

          {icon}

        </div>


        <div className="stat-info">

          <span>{title}</span>

          <h2>{value}</h2>

        </div>

      </div>


      {trendText && (
        <div className="stat-footer">
          {trend !== undefined && (
            <span className={trend >= 0 ? "trend-positive" : "trend-negative"}>
              {trend >= 0 ? "↑" : "↓"} {Math.abs(trend)}%
            </span>
          )}
          <span>{trendText}</span>
        </div>
      )}

    </div>

  );
}

export default StatCard;