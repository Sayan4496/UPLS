import hashlib
import json

from detection.format_detector import FormatDetector
from registry.parser_registry import get_parser

from normalization.normalizer import LogNormalizer
from normalization.service import save_normalized_event

from models.raw_event import RawEvent


class ProcessingService:

    def process(
        self,
        db,
        upload,
        raw_content
    ):

        # --------------------------------
        # STEP 1: Detect log format
        # --------------------------------

        detector = FormatDetector()

        file_format = detector.detect(
            raw_content
        )


        # --------------------------------
        # STEP 2: Get correct parser
        # --------------------------------

        parser = get_parser(
            file_format
        )


        # --------------------------------
        # STEP 3: Parse raw content
        # --------------------------------

        parsed_events = parser.parse(
            raw_content
        )


        # Make sure parsed_events is a list

        if isinstance(parsed_events, dict):

            parsed_events = [
                parsed_events
            ]


        # --------------------------------
        # STEP 4: Create normalizer
        # --------------------------------

        normalizer = LogNormalizer()


        raw_events_created = 0

        normalized_events_created = 0


        # --------------------------------
        # STEP 5: Process every event
        # --------------------------------

        for event in parsed_events:


            # Convert event to string

            if isinstance(event, dict):

                event_raw_content = json.dumps(
                    event
                )

            else:

                event_raw_content = str(
                    event
                )


            # --------------------------------
            # Generate checksum
            # --------------------------------

            checksum = hashlib.sha256(

                event_raw_content.encode(
                    "utf-8"
                )

            ).hexdigest()


            # --------------------------------
            # Save Raw Event
            # --------------------------------

            raw_event = RawEvent(

                upload_id=upload.id,

                raw_content=event_raw_content,

                original_format=file_format,

                checksum=checksum

            )


            db.add(
                raw_event
            )

            db.commit()

            db.refresh(
                raw_event
            )


            raw_events_created += 1


            # --------------------------------
            # Normalize event
            # --------------------------------

            normalized_data = normalizer.normalize(
                event
            )


            # --------------------------------
            # Save Normalized Event
            # --------------------------------

            save_normalized_event(

                db=db,

                raw_event_id=raw_event.id,

                normalized_data=normalized_data

            )


            normalized_events_created += 1


        # --------------------------------
        # Return result
        # --------------------------------

        return {

            "format": file_format,

            "parsed_events": len(
                parsed_events
            ),

            "raw_events_created": raw_events_created,

            "normalized_events_created":
                normalized_events_created

        }


    # ====================================
    # BACKWARD COMPATIBILITY METHOD
    # ====================================

    def process_file(
        self,
        db,
        upload,
        raw_content
    ):

        return self.process(

            db=db,

            upload=upload,

            raw_content=raw_content

        )