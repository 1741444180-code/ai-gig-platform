import api from './request';

/**
 * 需求相关 API
 */
export default {
  /**
   * 获取需求列表 (首页)
   * @param {Object} params { page, category, search }
   */
  getList(params = {}) {
    return api.request({ url: '/demands', method: 'GET', data: params });
  },

  /**
   * 发布需求
   * @param {Object} data 需求数据
   */
  publish(data) {
    return api.request({ url: '/demands', method: 'POST', data });
  },

  /**
   * 获取需求详情
   * @param {String|Number} id
   */
  getDetail(id) {
    return api.request({ url: `/demands/${id}`, method: 'GET' });
  },

  /**
   * 获取匹配的 Agent 列表
   * @param {String|Number} id 需求ID
   */
  getMatchingAgents(id) {
    return api.request({ url: `/demands/${id}/matching`, method: 'GET' });
  },

  /**
   * 手动指派 Agent 接单
   * @param {String|Number} id 需求ID
   * @param {Object} data { agent_id }
   */
  assignAgent(id, data) {
    return api.request({ url: `/demands/${id}/assign`, method: 'POST', data });
  },

  /**
   * 获取我的需求列表
   * @param {Object} params { status }  status: 0-发布中 1-进行中 2-已完成
   */
  getMyDemands(params = {}) {
    return api.request({ url: '/users/me/demands', method: 'GET', data: params });
  }
};
