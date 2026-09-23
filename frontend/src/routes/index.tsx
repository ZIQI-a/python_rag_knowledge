import {createBrowserRouter} from "react-router-dom";
import {BasicLayout} from "@/layouts/BasicLayout.tsx";
import {HomePage} from "@/pages/HomePage.tsx";


export const router = createBrowserRouter([
    {
        path: '/',
        element: <BasicLayout />,
        children: [{ index: true, element: <HomePage /> }],
    },
])
