import xml.etree.ElementTree as ET

from parsers.base_parser import BaseParser


class XMLParser(BaseParser):

    format_name = "XML"
    version = "1.0.0"

    def parse(self, raw_content: str):

        try:

            root = ET.fromstring(
                raw_content.strip()
            )


            events = []


            def flatten_element(
                element,
                prefix=""
            ):

                data = {}


                for child in element:

                    key = child.tag


                    if prefix:

                        key = (
                            f"{prefix}_{key}"
                        )


                    if len(child):

                        nested_data = flatten_element(
                            child,
                            key
                        )

                        data.update(
                            nested_data
                        )

                    else:

                        data[key] = (
                            child.text.strip()
                            if child.text
                            else ""
                        )


                # Include attributes

                for attr, value in element.attrib.items():

                    data[attr] = value


                return data


            # Root itself is event

            if root.tag.lower() == "event":

                event = flatten_element(root)

                events.append(event)


            else:

                # Find all event elements

                event_elements = root.findall(
                    ".//event"
                )


                # If no event tags exist

                if not event_elements:

                    event = flatten_element(root)

                    events.append(event)


                else:

                    for event_element in event_elements:

                        event = flatten_element(
                            event_element
                        )

                        events.append(event)


            return events


        except ET.ParseError as e:

            raise ValueError(

                f"XML parsing failed: {str(e)}"

            )