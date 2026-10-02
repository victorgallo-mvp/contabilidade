import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Kanban from './pages/Kanban'
import Revisao from './pages/Revisao'
import Clientes from './pages/Clientes'
import ClienteDetalhe from './pages/ClienteDetalhe'
import Historico from './pages/Historico'
import Portal from './pages/Portal'

function Protegido({ children }) {
  const { logado } = useAuth()
  return logado ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/c/:slug" element={<Portal />} />
      <Route path="/login" element={<Login />} />
      <Route element={<Protegido><Layout /></Protegido>}>
        <Route path="/" element={<Kanban />} />
        <Route path="/revisao" element={<Revisao />} />
        <Route path="/clientes" element={<Clientes />} />
        <Route path="/clientes/:id" element={<ClienteDetalhe />} />
        <Route path="/historico" element={<Historico />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
