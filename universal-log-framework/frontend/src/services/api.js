import axios from "axios";


const API_BASE_URLS = [

  typeof window !== "undefined" && window.location?.hostname
    ? `http://${window.location.hostname}:8000`
    : "http://localhost:8000",
  "http://localhost:8000",
  "http://127.0.0.1:8000"

];


const api = {

  get: (url, config = {}) => requestWithFallback(url, {
    ...config,
    method: "get"
  }),

  post: (url, data, config = {}) => requestWithFallback(url, {
    ...config,
    method: "post",
    data
  })

};


export const requestWithFallback = async (url, config = {}) => {

  let lastError = null;

  for (const baseUrl of API_BASE_URLS) {

    try {

      return await axios({
        ...config,
        url: `${baseUrl}${url}`
      });

    } catch (error) {

      lastError = error;
    }

  }

  throw lastError;

};


export const checkBackendHealth = async () => {

  try {

    const response = await requestWithFallback("/health");

    const connected =
      response?.data?.status === "healthy" ||
      response?.data?.database === "connected";

    return {
      connected,
      data: response?.data ?? null
    };

  } catch (error) {

    console.warn("Backend health check failed", error);

    return {
      connected: false,
      data: null
    };

  }

};


export const getEvents = async (params = {}) => {

  const response = await requestWithFallback("/events/", {
    method: "get",
    params
  });


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


export const exportEventsData = async (format = "json") => {

  const response = await api.get(`/api/v1/export/${format}`, {
    responseType: "blob"
  });

  return response;

};


export const previewParserLab = async (rawLog) => {

  const response = await api.post("/parser-lab/preview", {
    raw_log: rawLog
  });

  return response.data;

};


export const getProcessingJob = async (jobId) => {

  const response = await api.get(`/upload/jobs/${jobId}`);

  return response.data;

};


export const getProcessingJobs = async () => {

  const response = await api.get("/upload/jobs");

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