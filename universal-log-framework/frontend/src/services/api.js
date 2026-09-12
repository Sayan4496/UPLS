import axios from "axios";


const API_BASE_URL = "http://127.0.0.1:8000";


const api = axios.create({

  baseURL: API_BASE_URL,

  timeout: 5000,

});


export const checkBackendHealth = async () => {

  try {

    const response = await api.get("/health");


    return {

      connected:
        response.data.status === "healthy",

      data: response.data

    };


  } catch {

    console.warn("Backend health check failed");


    return {

      connected: false,

      data: null

    };

  }

};


export const getEvents = async (params = {}) => {

  const response = await api.get(

    "/events/",

    {
      params
    }

  );


  return response.data;

};


export const getEvent = async (eventId) => {

  const response = await api.get(`/events/${eventId}`);

  return response.data;

};


export const getEventStats = async () => {

  const response = await api.get("/events/stats");

  return response.data;

};


export const getParserCoverage = async () => {

  const response = await api.get("/analytics/parser-coverage");

  return response.data;

};


export const getAnalyticsDashboard = async () => {

  const response = await api.get("/analytics/dashboard");

  return response.data;

};


export const previewParserLab = async (rawLog) => {

  const response = await api.post("/parser-lab/preview", {
    raw_log: rawLog
  });

  return response.data;

};


export const getDashboardData = async () => {

  const response = await getEvents({

    page: 1,

    limit: 100

  });


  const events = response.events || [];


  const totalEvents =

    response.total_events || events.length;


  const highSeverity = events.filter(

    event =>

      event.severity?.toUpperCase() === "HIGH"

  ).length;


  const blockedEvents = events.filter(

    event =>

      event.action?.toUpperCase() === "BLOCKED"

  ).length;


  const activeSources = new Set(

    events

      .map(event => event.source_ip)

      .filter(Boolean)

  ).size;


  return {

    totalEvents,

    highSeverity,

    blockedEvents,

    activeSources,

    events

  };

};


export default api;