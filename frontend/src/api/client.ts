import { client } from '@/client/client.gen'
import { formatApiError } from "@/utils/errors.ts";
import {message} from "antd";


client.setConfig({
    baseUrl: '',
    throwOnError: true,
})

client.interceptors.response.use(async (response) => {
    if(!response.ok) {
        message.error(await formatApiError(response))
    }
    return response;
})
