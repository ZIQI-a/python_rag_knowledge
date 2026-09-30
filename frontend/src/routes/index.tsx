import {createBrowserRouter} from "react-router-dom";
import {BasicLayout} from "@/layouts/BasicLayout.tsx";
import {HomePage} from "@/pages/HomePage.tsx";
import {DocumentsPage} from "@/pages/DocumentsPage.tsx";
import {DocumentDetailPage} from "@/pages/DocumentDetailPage.tsx";


export const router = createBrowserRouter([
    {
        path: '/',
        element: <BasicLayout />,
        children: [
            { index: true, element: <HomePage /> },
            { path: 'documents', element: <DocumentsPage /> },
            { path: 'documents/:id', element: <DocumentDetailPage /> }
        ],
    },
])
