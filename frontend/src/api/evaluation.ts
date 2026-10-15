import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
    createEvaluationRun as sdkCreateEvaluationRun,
    deleteEvaluationRun as sdkDeleteEvaluationRun,
    getEvaluationRun as sdkGetEvaluationRun,
    listEvaluationDatasets as sdkListEvaluationDatasets,
    listEvaluationItems as sdkListEvaluationItems,
    listEvaluationRuns as sdkListEvaluationRuns,
    updateEvaluationItem as sdkUpdateEvaluationItem,
} from '@/client/sdk.gen'
import type {
    EvaluationItemRead,
    EvaluationItemUpdate,
    EvaluationRunRead,
} from '@/client/types.gen'
import {
    evaluationDatasetsKey,
    evaluationItemsKey,
    evaluationRunKey,
    evaluationRunsKey,
} from '@/api/queryKeys'


type BadCaseCategory = NonNullable<EvaluationItemRead['bad_case_category']>

/**
 * 获取评测run任务列表
 */
export function useEvaluationDatasets() {
    return useQuery({
        queryKey: evaluationDatasetsKey,
        queryFn: async () => (await sdkListEvaluationDatasets()).data,
    })
}

/**
 * 执行测评任务
 */
export function useEvaluationRuns(page = 1, pageSize = 20) {
    return useQuery({
        queryKey: [...evaluationRunsKey, page, pageSize],
        queryFn: async () => (
            await sdkListEvaluationRuns({ query: { page, page_size: pageSize } })
        ).data,
        // Running的状态会随进度实时变化，列表自动刷新
        refetchInterval: (query) => {
            const items = query.state.data?.items ?? []
            return items.some((r) => r.status === 'running') ? 5000 : false
        }
    })
}

/**
 * 获取评测Run单个详情，根据Run ID获取
 */
export function useEvaluationRun(runId: string | undefined) {
    return useQuery({
        queryKey: runId ? evaluationRunKey(runId) : ['evaluation-run', 'none'],
        enabled: Boolean(runId),
        queryFn: async () =>
            (await sdkGetEvaluationRun({ path: {run_id: runId!} })).data,
        refetchInterval: (query) => {
            const run = query.state.data as EvaluationRunRead | undefined
            return run?.status === 'running' ? 5000 : false
        }
    })
}

/**
 * 获取Items列表
 * @param runId
 * @param filters
 */
export function useEvaluationItems(
    runId: string | undefined,
    filters: {
        page: number
        pageSize: number
        badCaseOnly: boolean
        category: BadCaseCategory | null
    }
) {
    return useQuery({
        queryKey: runId
            ? evaluationItemsKey(runId, {
                badCaseOnly: filters.badCaseOnly,
                category: filters.category,
                page: filters.page
            }): ['evaluation-items', 'none'],
        enabled: Boolean(runId),
        queryFn: async () => (
            await sdkListEvaluationItems({
                path: {run_id: runId!},
                query: {
                    page: filters.page,
                    page_size: filters.pageSize,
                    bad_case_only: filters.badCaseOnly,
                    category: filters.category ?? undefined
                }
            })
        ).data,
    })
}

/**
 * 创建run评测
 */
export function useCreateEvaluationRun() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (body: { name: string; dataset_name:string }) =>
            (await sdkCreateEvaluationRun({body})).data,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: evaluationRunsKey })
        }
    })
}

/**
 * 删除run评测
 */
export function useDeleteEvaluationRun() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (runId: string) =>
            sdkDeleteEvaluationRun({ path: { run_id: runId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: evaluationRunsKey })
        }
    })
}

/**
 *  更新归因
 */
export function useUpdateEvaluationItem(runId: string) {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (params: { itemId: string; body: EvaluationItemUpdate }) =>
            (
                await sdkUpdateEvaluationItem({
                    path: { item_id: params.itemId },
                    body: params.body
                })
            ).data,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['evaluation-items', runId] })
            queryClient.invalidateQueries({ queryKey: evaluationRunKey(runId) })
        }
    })
}

export type { BadCaseCategory }
