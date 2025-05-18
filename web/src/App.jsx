import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./App.css";
import Drawer from "./components/Drawer";
import ChatApp from "./components/ChatApp";
import { API_BASE_URL } from "./constants";

// Redirect from root path to /chat with a new UUID
// or generate new UUID if at /chat without ID
if (
  window.location.pathname === "/" ||
  (window.location.pathname === "/chat" && !new URLSearchParams(window.location.search).get("id"))
) {
  const newId = crypto.randomUUID().toString().replace(/-/g, "");
  window.location.href = `/chat?id=${newId}`;
}

const defaultQueryFn = async ({ queryKey }) => {
  const endpoint = queryKey.join("/");
  const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
    credentials: "include",
  });
  return await response.json();
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: defaultQueryFn,
    },
  },
});

function App() {
  const urlParams = new URLSearchParams(window.location.search);
  const chatId = urlParams.get("id");

  return (
    <QueryClientProvider client={queryClient}>
      <Drawer chatId={chatId}>
        <ChatApp chatId={chatId} />
      </Drawer>
    </QueryClientProvider>
  );
}

export default App;
