/**
 * API Client for Frontend
 * Type-safe API calls to backend with error handling
 */

const API_BASE_URL = (() => {
    const envUrl = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
    // If URL starts with /, construct full URL from browser location
    if (typeof window !== 'undefined' && envUrl.startsWith('/')) {
        return `${window.location.protocol}//${window.location.hostname}:8000${envUrl}`;
    }
    return envUrl;
})();

interface ApiError {
    error: string;
    details?: string;
    timestamp: string;
}

interface Investigation {
    id: string;
    name: string;
    target: string;
    goal: string;
    status: string;
    created_by: string;
    created_at: string;
    updated_at: string;
    completed_at?: string;
}

interface CollectionJob {
    id: string;
    investigation_id: string;
    agent_type: string;
    query: string;
    status: string;
    started_at: string;
    completed_at?: string;
    items_collected: number;
    entities_discovered: number;
}

interface Entity {
    id: string;
    name: string;
    type: string;
    confidence: number;
    properties: Record<string, any>;
    sources: string[];
    first_seen: string;
    last_updated: string;
}

interface GraphData {
    nodes: Array<{
        id: string;
        label: string;
        type: string;
        confidence: number;
    }>;
    edges: Array<{
        id: string;
        source: string;
        target: string;
        label: string;
        confidence: number;
    }>;
}

class APIClient {
    private baseUrl: string;
    private token?: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    setToken(token: string) {
        this.token = token;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...options.headers as Record<string, string>,
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            if (!response.ok) {
                const error: ApiError = await response.json();
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    // ============================================
    // Investigations
    // ============================================

    async createInvestigation(data: {
        name: string;
        target: string;
        goal: string;
    }): Promise<{ investigation: Investigation }> {
        return this.request('/investigations/create', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async listInvestigations(skip: number = 0, limit: number = 50): Promise<{
        investigations: Investigation[];
        total: number;
    }> {
        return this.request(`/investigations?skip=${skip}&limit=${limit}`);
    }

    async getInvestigation(id: string): Promise<{
        investigation: Investigation;
        entity_count: number;
        collection_job_count: number;
        hypothesis_count: number;
    }> {
        return this.request(`/investigations/${id}`);
    }

    async deleteInvestigation(id: string): Promise<{ message: string }> {
        return this.request(`/investigations/${id}`, {
            method: 'DELETE',
        });
    }

    // ============================================
    // Collection
    // ============================================

    async startCollection(data: {
        investigation_id: string;
        agent_type: string;
        query: string;
        max_results?: number;
    }): Promise<{ job: CollectionJob; progress_percent: number }> {
        return this.request('/collection/start', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getCollectionJob(jobId: string): Promise<{
        job: CollectionJob;
        progress_percent: number;
    }> {
        return this.request(`/collection/jobs/${jobId}`);
    }

    async listCollectionJobs(investigationId?: string): Promise<
        Array<{ job: CollectionJob; progress_percent: number }>
    > {
        const query = investigationId ? `?investigation_id=${investigationId}` : '';
        return this.request(`/collection/jobs${query}`);
    }

    async getCollectionSources(): Promise<{
        sources: Array<{
            id: string;
            name: string;
            description: string;
            requires_api_key: boolean;
            collection_types: string[];
        }>;
    }> {
        return this.request('/collection/sources');
    }

    // ============================================
    // Entities & Graph
    // ============================================

    async searchEntities(data: {
        query: string;
        investigation_id?: string;
        entity_type?: string;
        min_confidence?: number;
        limit?: number;
    }): Promise<{ entities: Entity[]; total: number }> {
        return this.request('/entities/search', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getEntity(id: string): Promise<{
        entity: Entity;
        relationships: any[];
    }> {
        return this.request(`/entities/${id}`);
    }

    async getGraph(investigationId: string, maxNodes: number = 100): Promise<{
        graph: GraphData;
        investigation_id: string;
        node_count: number;
        edge_count: number;
    }> {
        return this.request('/entities/graph/query', {
            method: 'POST',
            body: JSON.stringify({
                investigation_id: investigationId,
                max_nodes: maxNodes,
            }),
        });
    }

    // ============================================
    // Reasoning
    // ============================================

    async generatePlan(data: {
        investigation_id: string;
        goal: string;
        llm_provider?: string;
    }): Promise<{
        investigation_id: string;
        tasks: any[];
        strategy_notes: string;
        llm_provider: string;
    }> {
        return this.request('/reasoning/plan', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async generateHypotheses(data: {
        investigation_id: string;
        graph_context?: Record<string, any>;
        text_context?: string;
        llm_provider?: string;
    }): Promise<{
        hypotheses: any[];
        investigation_id: string;
        llm_provider: string;
    }> {
        return this.request('/reasoning/hypotheses', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getAvailableModels(): Promise<{
        models: Array<{
            provider: string;
            model_name: string;
            available: boolean;
            description: string;
        }>;
        default_provider: string;
    }> {
        return this.request('/reasoning/models');
    }

    // ============================================
    // Authentication
    // ============================================

    async login(username: string, password: string): Promise<{
        token: { access_token: string; token_type: string; expires_in: number };
        user: any;
    }> {
        const response = await this.request<any>('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });

        if (response.token?.access_token) {
            this.setToken(response.token.access_token);
        }

        return response;
    }

    async register(data: {
        username: string;
        email: string;
        password: string;
        role?: string;
    }): Promise<{ user: any }> {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getCurrentUser(): Promise<{ user: any }> {
        return this.request('/auth/me');
    }

    // ============================================
    // Health Check
    // ============================================

    async healthCheck(): Promise<{ status: string; services: Record<string, string> }> {
        return this.request('/health/detailed', {
            method: 'GET',
        });
    }
}

// Singleton instance
const apiClient = new APIClient();

export default apiClient;
export type { Investigation, CollectionJob, Entity, GraphData };
