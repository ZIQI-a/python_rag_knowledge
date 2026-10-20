import {NotFoundPage, PageLoading, RouteErrorPage} from '@/components/PageState'
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
import {PageTitleLayout} from "@/components/PageTitleLayout.tsx";

export const router = createBrowserRouter([
    {
        element: <PageTitleLayout />,
        errorElement: <RouteErrorPage/>,
        hydrateFallbackElement: <PageLoading/>,
        children: [
            // 登录单独路由
            { path: '/login', element: <LoginPage /> },
            {
                path: '/',
                element: <RequireAuth />,
                children: [
                    {
                        element: <BasicLayout />,
                        children: [
                            { index: true, element: <HomePage />, errorElement: <RouteErrorPage/> },
                            { path: 'documents', element: <DocumentsPage />, errorElement: <RouteErrorPage/> },
                            { path: 'documents/:id', element: <DocumentDetailPage />, errorElement: <RouteErrorPage/> },
                            { path: '*', element: <NotFoundPage/> },
                            { path: 'chat', element: <ChatPage />, errorElement: <RouteErrorPage/>},
                            // admin only
                            {
                                element: <RequireAdmin />,
                                children: [
                                    { path: 'evaluation', element: <EvaluationListPage />, errorElement: <RouteErrorPage/> },
                                    { path: 'evaluation/runs/:id', element: <EvaluationDetailPage />, errorElement: <RouteErrorPage/> },
                                    { path: 'users', element: <UserPage />, errorElement: <RouteErrorPage/> },
                                    { path: 'roles', element: <RolesPage />, errorElement: <RouteErrorPage/> },
                                ]
                            }
                        ]
                    }
                ],
            },
        ],
    },
])
