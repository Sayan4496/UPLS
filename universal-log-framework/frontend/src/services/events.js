import { getEvents, getEventStats } from "./api";

export const fetchEvents = async (params = {}) => {
  try {
    return await getEvents(params);
  } catch (error) {
    console.error("Error fetching events:", error);
    throw error;
  }
};

export const fetchEventStats = async () => {
  try {
    return await getEventStats();
  } catch (error) {
    console.error("Error fetching event stats:", error);
    throw error;
  }
};