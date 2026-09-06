from normalization.schema import NormalizedLogSchema
from datetime import datetime, timezone


class LogNormalizer:

    def get_value(self, data: dict, *keys, default=None):
        """
        Return the first valid value found from the provided keys.
        """

        for key in keys:

            value = data.get(key)

            if value is not None and str(value).strip() != "":

                return value

        return default


    def normalize_timestamp(self, timestamp):

        # No timestamp available
        if not timestamp:

            return datetime.now(timezone.utc)


        # Already datetime object
        if isinstance(timestamp, datetime):

            if timestamp.tzinfo is None:

                return timestamp.replace(
                    tzinfo=timezone.utc
                )

            return timestamp


        timestamp = str(timestamp).strip()


        # ISO 8601 format
        try:

            parsed_time = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

            if parsed_time.tzinfo is None:

                parsed_time = parsed_time.replace(
                    tzinfo=timezone.utc
                )

            return parsed_time

        except (ValueError, TypeError):

            pass


        # Syslog timestamp
        try:

            current_year = datetime.now().year

            parsed_time = datetime.strptime(

                f"{current_year} {timestamp}",

                "%Y %b %d %H:%M:%S"

            )

            return parsed_time.replace(
                tzinfo=timezone.utc
            )

        except (ValueError, TypeError):

            pass


        # Common timestamp formats

        date_formats = [

            "%Y-%m-%d %H:%M:%S",

            "%Y-%m-%d %H:%M:%S.%f",

            "%Y/%m/%d %H:%M:%S",

            "%d/%m/%Y %H:%M:%S",

            "%m/%d/%Y %H:%M:%S",

            "%d-%m-%Y %H:%M:%S",

            "%m-%d-%Y %H:%M:%S"

        ]


        for date_format in date_formats:

            try:

                parsed_time = datetime.strptime(
                    timestamp,
                    date_format
                )

                return parsed_time.replace(
                    tzinfo=timezone.utc
                )

            except ValueError:

                continue


        print(
            f"WARNING: Could not parse timestamp: {timestamp}"
        )


        return datetime.now(timezone.utc)


    def normalize_severity(self, severity):

        if severity is None:

            return "UNKNOWN"


        severity = str(severity).strip().upper()


        severity_map = {

            # Numeric severity

            "0": "LOW",
            "1": "LOW",
            "2": "LOW",

            "3": "MEDIUM",
            "4": "MEDIUM",
            "5": "MEDIUM",

            "6": "HIGH",
            "7": "HIGH",

            "8": "CRITICAL",
            "9": "CRITICAL",
            "10": "CRITICAL",


            # Text severity

            "INFO": "LOW",

            "INFORMATION": "LOW",

            "WARNING": "MEDIUM",

            "WARN": "MEDIUM",

            "ERROR": "HIGH",

            "FATAL": "CRITICAL"

        }


        return severity_map.get(
            severity,
            severity
        )


    def normalize(self, parsed_data: dict) -> NormalizedLogSchema:


        # ==========================================
        # DEBUG: SHOW EXACT INPUT TO NORMALIZER
        # ==========================================

        print("\n")
        print("==========================================")
        print("       NORMALIZER INPUT")
        print("==========================================")
        print(parsed_data)
        print("==========================================")
        print("\n")


        # ==========================================
        # TIMESTAMP
        # ==========================================

        raw_timestamp = self.get_value(

            parsed_data,

            "timestamp",

            "event_timestamp",

            "time",

            "datetime",

            "date",

            "devTime",

            "rt",

            "start_time",

            "end_time"

        )


        timestamp = self.normalize_timestamp(
            raw_timestamp
        )


        # ==========================================
        # SOURCE IP
        # ==========================================

        source_ip = self.get_value(

            parsed_data,

            "source_ip",

            "src",

            "src_ip",

            "source",

            "sourceAddress",

            "source_address",

            "saddr",

            "client_ip",

            "clientip"

        )


        # ==========================================
        # DESTINATION IP
        # ==========================================

        destination_ip = self.get_value(

            parsed_data,

            "destination_ip",

            "dst",

            "dst_ip",

            "destination",

            "destinationAddress",

            "destination_address",

            "daddr",

            "server_ip",

            "serverip"

        )


        # ==========================================
        # SOURCE PORT
        # ==========================================

        source_port = self.get_value(

            parsed_data,

            "source_port",

            "src_port",

            "spt",

            "sport",

            "sourcePort",

            "srcPort"

        )


        # ==========================================
        # DESTINATION PORT
        # ==========================================

        destination_port = self.get_value(

            parsed_data,

            "destination_port",

            "dst_port",

            "dpt",

            "dport",

            "destinationPort",

            "dstPort"

        )


        # ==========================================
        # SEVERITY
        # ==========================================

        raw_severity = self.get_value(

            parsed_data,

            "severity",

            "sev",

            "level",

            "priority",

            "risk_level"

        )


        severity = self.normalize_severity(
            raw_severity
        )


        # ==========================================
        # EVENT TYPE
        # ==========================================

        event_type = self.get_value(

            parsed_data,

            "event_type",

            "eventType",

            "type",

            "cat",

            "category",

            "event_name",

            "name",

            "event",

            "signature_id"

        )


        # ==========================================
        # ACTION
        # ==========================================

        action = self.get_value(

            parsed_data,

            "action",

            "act",

            "deviceAction",

            "device_action",

            "outcome",

            "result",

            "status"

        )


        # ==========================================
        # DEVICE TYPE
        # ==========================================

        device_type = self.get_value(

            parsed_data,

            "device_type",

            "deviceType",

            "device",

            "product",

            "program",

            "service"

        )


        # ==========================================
        # VENDOR
        # ==========================================

        vendor = self.get_value(

            parsed_data,

            "vendor",

            "device_vendor",

            "manufacturer",

            "deviceVendor"

        )


        # ==========================================
        # MESSAGE
        # ==========================================

        message = self.get_value(

            parsed_data,

            "message",

            "msg",

            "event_message",

            "event_name",

            "name",

            "description",

            "details",

            "reason"

        )


        # ==========================================
        # DEBUG: SHOW NORMALIZED VALUES
        # ==========================================

        print("NORMALIZED VALUES:")

        print(f"Timestamp: {timestamp}")

        print(f"Source IP: {source_ip}")

        print(f"Destination IP: {destination_ip}")

        print(f"Source Port: {source_port}")

        print(f"Destination Port: {destination_port}")

        print(f"Severity: {severity}")

        print(f"Event Type: {event_type}")

        print(f"Action: {action}")

        print(f"Device Type: {device_type}")

        print(f"Vendor: {vendor}")

        print(f"Message: {message}")

        print("==========================================")
        print("\n")


        # ==========================================
        # CREATE UNIVERSAL LOG
        # ==========================================

        normalized_log = NormalizedLogSchema(

            event_timestamp=timestamp,

            source_ip=source_ip,

            destination_ip=destination_ip,

            source_port=source_port,

            destination_port=destination_port,

            severity=severity,

            event_type=event_type,

            action=action,

            device_type=device_type,

            vendor=vendor,

            message=message

        )


        return normalized_log