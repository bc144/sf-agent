import { BrowserRouter, Routes, Route } from "react-router-dom";
import ProductSearch from "./components/ProductSearch";

function App() {  
  return (
    <div>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ProductSearch />} />

          {/* Ruta 404: debe ir al final */}
          {/* <Route path="*" element={<NotFoundPage />} /> */}
        </Routes>
      </BrowserRouter>
      {/* <Toaster /> */}
    </div>
  );
}

export default App;
