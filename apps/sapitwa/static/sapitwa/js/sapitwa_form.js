'use strict';

var sapitwaSelectionTemplate = function (tag, container) {
    var $tag = $(
        '<span>' + tag.text + '</span>'
    );
    container[0].style.background = tag.element.dataset.color;
    return $tag;
}

var sapitwaResultTemplate = function (tag) {
    if (!tag.element) { return ''; }
    var $tag = $(
        '<span>' + tag.text + '</span>'
    );
    return $tag;
}

jQuery(document).ready(function() {
    $('.select2-tags').select2({
        templateSelection: sapitwaSelectionTemplate,
        templateResult: sapitwaResultTemplate,
        width: '100%'
    });
});
