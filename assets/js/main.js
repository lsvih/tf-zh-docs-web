$(document).ready(() => {
    $('pre code').each((i, block) => {
        hljs.highlightBlock(block);
    });
    // 如果 nav 数据存在则渲染左侧菜单
    if (nav) {
        nav.forEach((e, i) => {
            if (e.type === "child") {
                $("#left-nav").html($("#left-nav").html() + firstClassChildNav(e.title, e.link))
            } else {
                $("#left-nav").html($("#left-nav").html() + parentNav(e.title, e.sub_class))
            }
        })
    }
});


function firstClassChildNav(name, link) {
    return `
    <h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
        <span>${name}</span>
        <a class="d-flex align-items-center text-muted" href="${link}">
            <span data-feather="plus-circle"></span>
        </a>
    </h6>`
}

function parentNav(name, child) {
    var item = document.createElement("div");
    item.innerHTML = `<h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
        <span>${name}</span>
        <a class="d-flex align-items-center text-muted" href="#">
            <span data-feather="plus-circle"></span>
        </a>
    </h6>
    <ul class="nav flex-column mb-2">
    </ul>`
    child.forEach((e, i) => {
        $(item.getElementsByClassName("nav")[0]).append(childNav(e.title, e.link))
    })
    return item.innerHTML

    function childNav(name, link) {
        return `<li class="nav-item">
            <a class="nav-link" href="${link}">
            <span data-feather="file-text"></span>
        ${name}
        </a>
        </li>`
    }
}