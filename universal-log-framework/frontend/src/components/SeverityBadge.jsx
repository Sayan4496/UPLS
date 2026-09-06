function SeverityBadge({ severity }) {

  return (
    <span className={`severity ${severity.toLowerCase()}`}>
      {severity}
    </span>
  );

}

export default SeverityBadge;