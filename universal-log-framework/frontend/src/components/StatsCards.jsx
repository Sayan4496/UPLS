function StatsCards() {
  const stats = [
    {
      title: "Total Events",
      value: "16",
      icon: "📊",
      type: "blue"
    },
    {
      title: "High Severity",
      value: "8",
      icon: "⚠",
      type: "red"
    },
    {
      title: "Blocked Events",
      value: "12",
      icon: "🛡",
      type: "orange"
    },
    {
      title: "Active Sources",
      value: "5",
      icon: "🌐",
      type: "purple"
    }
  ];

  return (
    <section className="stats-grid">
      {stats.map((stat, index) => (
        <div className={`stat-card ${stat.type}`} key={index}>

          <div className="stat-icon">
            {stat.icon}
          </div>

          <div className="stat-info">
            <p>{stat.title}</p>
            <h3>{stat.value}</h3>
          </div>

        </div>
      ))}
    </section>
  );
}

export default StatsCards;