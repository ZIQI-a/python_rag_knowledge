import {createBrowserRouter} from "react-router-dom";
import {BasicLayout} from "@/layouts/BasicLayout.tsx";
import {HomePage} from "@/pages/HomePage.tsx";
import {DocumentsPage} from "@/pages/DocumentsPage.tsx";
import {DocumentDetailPage} from "@/pages/DocumentDetailPage.tsx";
import {ChatPage} from "@/pages/ChatPage.tsx";
import {EvaluationListPage} from "@/pages/EvaluationListPage.tsx";
import {EvaluationDetailPage} from "@/pages/EvaluationDetailPage.tsx";
import {LoginPage} from "@/pages/LoginPage.tsx";
import {UserPage} from "@/pages/UserPage.tsx";
import {RolesPage} from "@/pages/RolesPage.tsx";
import {RequireAuth} from "@/components/RequireAuth.tsx";
import {RequireAdmin} from "@/components/RequireAdmin.tsx";


export const router = createBrowserRouter([
    // 登录单独路由
    { path: '/login', element: <LoginPage /> },
    {
        path: '/',
        element: <RequireAuth />,
        children: [
            {
                element: <BasicLayout />,
                children: [
                    { index: true, element: <HomePage /> },
                    { path: 'documents', element: <DocumentsPage /> },
                    { path: 'documents/:id', element: <DocumentDetailPage /> },
                    { path: 'chat', element: <ChatPage />},
                    // admin only
                    {
                        element: <RequireAdmin />,
                        children: [
                            { path: 'evaluation', element: <EvaluationListPage /> },
                            { path: 'evaluation/runs/:id', element: <EvaluationDetailPage /> },
                            { path: 'users', element: <UserPage /> },
                            { path: 'roles', element: <RolesPage /> },
                        ]
                    }
                ]
            }
        ],
    },
])
