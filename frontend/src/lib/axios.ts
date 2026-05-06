import axios from "axios";
import toast from "react-hot-toast";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" }
});

api.interceptors.response.use(
  (response) => response.data.data,
  (error) => {
    const message = error.response?.data?.error ?? "Something went wrong";
    toast.error(typeof message === "string" ? message : "Something went wrong");
    return Promise.reject(
      new Error(typeof message === "string" ? message : "Something went wrong")
    );
  }
);

export const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
